# -*- coding: UTF-8 -*-
#
# Copyright © 2017 Alex Forster. All rights reserved.
# This software is licensed under the 3-Clause ("New") BSD license.
# See the LICENSE file for details.
#


import os
import logging
import traceback
import re

from datetime import datetime, timedelta
from select import select

from ptyprocess import PtyProcess
from pyte.streams import ByteStream
from pyte.screens import Screen

from sisqo.configuration import Configuration


class NotConnectedError(Exception): pass


class NotAuthenticatedError(Exception): pass


class AlreadyAuthenticatedError(Exception): pass


class BadAuthenticationError(Exception): pass


def onConnectionPrompt(prompt, state, logger):
    """
    :type prompt: str
    :type state: dict[str, Any]
    :type logger: logging.Logger
    :rtype: str|None
    """

    prompt = prompt.lower()

    state.setdefault('triedPassword', 0)

    state.setdefault('triedKeys', {})

    if 'enter passphrase for key' in prompt:

        key = re.findall( r'key \'(.+)\':\s*$', prompt, flags = re.IGNORECASE | re.MULTILINE )
        if key is None or len(key) != 1: key = '???'
        else: key = key[0]

        state['triedKeys'].setdefault(key, 0)

        if state['triedKeys'][key] > 2:

            logger.error('incorrect passphrase (after 3 attempts)')
            return None

        else:

            state['triedKeys'][key] += 1
            state['triedPassword'] = 0  # reset password failed attempts after successful passphrase

            logger.debug('trying key \'{}\''.format(key))

            return state['passphrase']

    if 'password:' in prompt:

        if state['triedPassword'] > 2:

            logger.error('incorrect password (after 3 attempts)')
            return None

        else:

            state['triedPassword'] += 1
            state['triedKeys'] = {}  # reset passphrase failed attempts after successful password

            logger.debug('trying password')

            return state['password']

    return None


class SSH(object):

    SCREEN_WIDTH = 512
    SCREEN_HEIGHT = 256

    class LoggerAdapter(logging.LoggerAdapter):

        def __init__(self, prefix, logger):

            super(SSH.LoggerAdapter, self).__init__(logger, {})
            self.prefix = prefix

        def process(self, msg, kwargs):

            return '{}@{:x} - {}'.format(self.prefix, id(self), msg), kwargs

    def __init__(self, host, port=22, username=None, timeout=10, sshOptions=None, logger=None):
        """
        :type host: str
        :type port: int
        :type username: str|None
        :type timeout: int
        :type sshOptions: list|None
        :type logger: logging.Logger|None
        """

        self._host = host
        """:type: str"""
        self._port = port if isinstance(timeout, int) else 22
        """:type: int"""
        self._username = username
        """:type: str"""
        self._timeout = timeout if isinstance(timeout, int) else 10
        """:type: int"""
        self._sshOptions = sshOptions or []
        """:type: list"""
        self._log = SSH.LoggerAdapter(self._host, logger or logging.getLogger('sisqo').addHandler(logging.NullHandler()))
        """:type: logging.Logger"""

        self._promptRegex = r'^[^\s]+[>#]\s?$'
        """:type: str"""
        self._moreRegex = r'^.*-+.*more.*-+.*$'
        """:type: str"""

        self._authenticated = False
        """:type: bool"""
        self._readSinceWrite = False
        """:type: bool"""

        self._readHandler = []
        self._writeHandler = []

        args = ['ssh']
        args.extend(self._sshOptions)
        args.extend(['-oConnectTimeout={}'.format(self._timeout)] if isinstance(timeout, int) else [])
        args.extend(['-p', self._port] if isinstance(self._port, int) and self._port != 22 else [])
        args.extend([(username + '@' if username else '') + self._host])

        self._pty = PtyProcess.spawn(args, dimensions=(SSH.SCREEN_HEIGHT, SSH.SCREEN_WIDTH), env={'TERM': 'vt100'})
        """:type: ptyprocess.PtyProcess"""
        self._vt = Screen(SSH.SCREEN_WIDTH, SSH.SCREEN_HEIGHT)
        """:type: pyte.Screen"""
        self._stream = ByteStream()
        """:type: pyte.ByteStream"""

        self._stream.attach(self._vt)

        self._log.debug('opened vty with `{}`'.format(' '.join(args)))

    def __repr__(self):
        """
        :rtype: str
        """
        return '<SSH host="{}" port={}>'.format(self._host, self._port)

    @property
    def host(self):
        """
        :rtype: str
        """
        return self._host

    @property
    def port(self):
        """
        :rtype: int
        """
        return self._port

    @property
    def promptRegex(self):
        """
        :rtype: str
        """
        return self._promptRegex

    @promptRegex.setter
    def promptRegex(self, value):

        self._promptRegex = value

    @property
    def moreRegex(self):
        """
        :rtype: str
        """
        return self._moreRegex

    @moreRegex.setter
    def moreRegex(self, value):

        self._moreRegex = value

    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.disconnect()

    def __del__(self):

        self.disconnect()

    def disconnect(self):

        if self._pty:

            self._pty.terminate(force=True)

            self._authenticated = False

            self._pty = None
            self._stream = None
            self._vt = None

            self._readSinceWrite = False

            self._log.info('disconnected')

    def _read(self, timeout=None, stripPrompt=True, promptRegex=None):
        """
        :type timeout: int|None
        :type stripPrompt: bool
        :type promptRegex: str|None
        :rtype: str
        """

        self._assertConnectionState(connected=True)

        if not promptRegex:

            promptRegex = self.promptRegex

        deadline = datetime.utcnow() + timedelta(seconds=timeout or self._timeout)

        eof = False
        self._vt.reset()

        while True:

            try:

                read = self._recv()

                if read is not None:

                    deadline = datetime.utcnow() + timedelta(seconds=timeout or self._timeout)

                    self._stream.feed(read)

                    if self._vt.cursor.y > self._vt.lines * 0.5:

                        self._vt.save_cursor()
                        self._vt.resize(self._vt.lines * 2, SSH.SCREEN_WIDTH)
                        self._vt.restore_cursor()

                    continue

            except EOFError:

                self._log.debug('EOF received')
                eof = True
                break

            line = self._vt.buffer[self._vt.cursor.y]
            line = ''.join(map(lambda l: l.data, line)).strip()

            if re.match(promptRegex, line, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                break

            if re.match(self._moreRegex, line, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                self._send(' ')
                continue

            if datetime.utcnow() > deadline:

                self._log.info('read timeout - could not match prompt regex or more pagination regex '
                               '(last regex match attempted against "{}")'
                               .format(line))
                break

        lines = []

        vtlines = [l.rstrip() for l in self._vt.display[0:self._vt.cursor.y+1]]

        for fn in self._readHandler:
            fn('\n'.join(vtlines))

        for line in vtlines:  # .rstrip() because unused vty cells are rendered as spaces

            if stripPrompt and re.match(promptRegex, line, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                continue

            lines.append(line)

        result = '\n'.join(lines)

        self._readSinceWrite = True

        if eof:

            self.disconnect()

        return result

    def read(self, timeout=None, stripPrompt=True, promptRegex=None):
        """
        :type timeout: int|None
        :type stripPrompt: bool
        :type promptRegex: str|None
        :rtype: str
        """

        self._assertConnectionState(connected=True, authenticated=True)

        return self._read(timeout=timeout or self._timeout, promptRegex=promptRegex, stripPrompt=stripPrompt)

    def _write(self, command, timeout=None, consumeEcho=True, mask=False):
        """
        :type command: str
        :type timeout: int|None
        :type consumeEcho: bool
        """

        self._assertConnectionState(connected=True)

        command = command.replace('?', '\x16?')

        if not self._readSinceWrite:

            self._read(stripPrompt=False)

        self._readSinceWrite = False

        if not command.endswith('\n'):

            command.rstrip('\r\n')
            command += '\n'

        self._send(command, mask=mask)

        if not consumeEcho:

            return

        # consume what's echoed back

        readLen = len(command)

        deadline = datetime.utcnow() + timedelta(seconds=timeout or self._timeout)

        while readLen > 0:

            recvd = self._recv(readLen)

            if b'\r' in recvd:
                recvd = recvd.replace(b'\r', b'')

            if recvd is not None:

                deadline = datetime.utcnow() + timedelta(seconds=timeout or self._timeout)
                self._stream.feed(recvd)
                readLen -= len(recvd)

            elif datetime.utcnow() > deadline:

                break

    def write(self, command, timeout=None, consumeEcho=True):
        """
        :type command: str
        :type timeout: int|None
        :type consumeEcho: bool
        """

        self._assertConnectionState(connected=True, authenticated=True)

        self._write(command, timeout=timeout or self._timeout, consumeEcho=consumeEcho)

    def authenticate(self, password=None, passphrase=None, promptCallback=onConnectionPrompt, promptState=None):
        """
        :type password: str|None
        :type passphrase: str|None
        :type promptCallback: (str, dict[str, object], logging.Logger) => bool|None
        :type promptState: dict|None
        :rtype: bool
        """
        try:

            self._assertConnectionState(connected=True, authenticated=False)

        except Exception as ex:

            self._log.error(self._formatException(ex, 'could not connect'))
            return False

        state = {
            'password': password,
            'passphrase': passphrase
        }

        if isinstance(promptState, dict):

            state.update(promptState)

        while True:

            prompt = self._read(promptRegex=r'.{5,}', stripPrompt=False)

            # if we appear to be authenticated...
            if re.findall(self._promptRegex, prompt, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                self._log.info('authenticated')

                self._authenticated = True

                break

            result = promptCallback(prompt, state, self._log)

            if result is None:

                break

            self._write(result, consumeEcho=False, mask=True)

        return self._authenticated

    def enable(self, password):
        """
        :type password: str
        :rtype: bool
        """

        self._assertConnectionState(connected=True, authenticated=True)

        self.write('enable')

        prompt = self.read(promptRegex=r'^.*password:.*$', stripPrompt=False).lower()

        if 'password:' not in prompt.lower():

            self._log.warn('remote did not prompt for an enable password')
            return True

        self._write(password, consumeEcho=False, mask=True)

        passwordResult = self.read(stripPrompt=False).lower()

        if 'password:' in passwordResult.lower() or 'denied' in passwordResult.lower():

            self._log.error('enable failed: incorrect password')
            return False

        self._log.info('enabled')

        return True

    def showRunningConfig(self):
        """
        :rtype: Configuration
        """
        self.write('show running-config')

        result = self.read()

        return Configuration(result)

    def showStartupConfig(self):
        """
        :rtype: Configuration
        """
        self.write('show startup-config')

        result = self.read()

        return Configuration(result)

    def onRead(self, func):

        self._readHandler.append(func)

    def onWrite(self, func):

        self._writeHandler.append(func)

    def _send(self, value, mask=False):
        """
        :type value: str
        """

        self._assertConnectionState(connected=True)

        self._pty.write(bytearray(value, encoding='utf-8'))

        for fn in self._writeHandler:
            fn(' {}'.format(re.sub(r'[^\r\n]', '*', value) if mask else value))

    def _recv(self, nr=1024):
        """
        :type nr: int
        :rtype: str
        """

        self._assertConnectionState(connected=True)

        canRead = self._pty.fd in select([self._pty.fd], [], [], 0.1)[0]
        if not canRead: return None

        result = os.read(self._pty.fd, nr)

        return result

    def _formatException(self, exception, message):
        """
        :type exception: Exception
        :type message: str
        :rtype: str
        """
        stack = traceback.extract_stack()

        exceptionMessage = traceback.format_exception_only(type(exception), exception)[0].strip()
        file = stack[-2][0]
        line = stack[-2][1]
        function = stack[-2][2]

        return '%s: %s in %s at %s:%d' % (message, exceptionMessage, function, file, line)

    def _assertConnectionState(self, connected=None, authenticated=None):
        """
        :type connected: bool|None
        :type authenticated: bool|None
        """

        if connected:

            if not self._pty or not self._pty.isalive():

                raise NotConnectedError('no SSH connection is established')

        if authenticated:

            if not self._authenticated:

                raise NotAuthenticatedError('SSH connection has not authenticated')

        elif authenticated == False:

            if self._authenticated:

                raise AlreadyAuthenticatedError('SSH connection has already authenticated')
