#!/usr/bin/env python
# -*- coding: utf-8 -*-
########################################################################################################################
# Copyright © 2015 Alex Forster. All rights reserved.
# This software is licensed under the 3-Clause ("New") BSD license.
# See the LICENSE file for details.
########################################################################################################################


import os
import logging
import traceback
import re

from datetime import datetime, timedelta

import paramiko
from pyte.streams import ByteStream
from pyte.screens import Screen

from Configuration import Configuration


class NotConnectedError(Exception): pass


class AlreadyConnectedError(Exception): pass


class NotAuthenticatedError(Exception): pass


class AlreadyAuthenticatedError(Exception): pass


class SSH:

    def __init__(self, host, port=22, proxyCommand=None):
        """
        :type host: str
        :type port: int
        :type proxyCommand: str|None
        """
        self._log = logging.getLogger(__name__)
        """:type: logging.Logger"""

        self._host = str(host)
        """:type: str"""
        self._port = int(port)
        """:type: int"""

        self._proxyCommand = str(proxyCommand)
        """:type: str"""

        self._proxySocket = None
        """:type: paramiko.ProxyCommand"""
        self._client = None
        """:type: paramiko.SSHClient"""
        self._shell = None
        """:type: paramiko.Channel"""

        self._readSinceWrite = None
        """:type: bool"""

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
    def proxyCommand(self):
        """
        :rtype: str
        """
        return self._proxyCommand

    def __enter__(self):

        proxyCommand = self._proxyCommand.replace('%h', self._host).replace('%p', str(self._port)) \
            if self._proxyCommand else None

        self._proxySocket = paramiko.ProxyCommand(proxyCommand) if proxyCommand else None
        self._client = paramiko.SSHClient()
        self._shell = None

        self._readSinceWrite = False

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        if self._proxySocket:

            self._proxySocket.close()

        if self._client:

            self._client.close()

        self._proxySocket = None
        self._client = None
        self._shell = None

        self._readSinceWrite = None

    def authenticate(self, username, password=None, privateKeyFile=None, privateKeyPassword=None):
        """
        :type username: str
        :type password: str|None
        :type privateKeyFile: str|None
        :type privateKeyPassword: str|None
        :rtype: bool
        """
        try:

            self._assertInContext()
            self._assertConnectionState(connected=False)

        except Exception as ex:

            self._log.error(self._formatException(ex, 'Could not authenticate with the remote host'))
            return False

        try:

            username = str(username)
            password = str(password) if password else password
            privateKeyFile = os.path.abspath(os.path.expanduser(str(privateKeyFile))) if privateKeyFile else None
            privateKeyPassword = str(privateKeyPassword) if privateKeyPassword else privateKeyPassword

            self._log.info('Connecting to %s as "%s"%s%s' % (
                self._host,
                username,
                ' using password authentication' if password else '',
                ' with an SSH keypair' if privateKeyFile else ''))

            self._client.set_log_channel(__name__)
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            pkey = None

            if privateKeyFile and privateKeyPassword:

                pkey = paramiko.RSAKey.from_private_key_file(privateKeyFile, password=privateKeyPassword)

            self._client.connect(
                timeout=30,
                banner_timeout=10,
                hostname=self._host,
                port=self._port,
                sock=self._proxySocket,
                allow_agent=False,
                look_for_keys=False,
                compress=False,
                username=username,
                password=password,
                pkey=pkey )

            self._log.info('Creating a vt100 512x64 shell')

            self._shell = self._client.invoke_shell(width=512, height=64)

            self._shell.set_combine_stderr(True)

            return True

        except Exception as ex:

            self._log.error(self._formatException(ex, 'Could not connect to the remote host'))
            return False

    def read(self, timeout=10, promptRegex=r'^.*[>#]\s*$', moreRegex=r'^.*-+\s*more\s*-+.*$', stripPrompt=True):
        """
        :type timeout: int
        :type promptRegex: str
        :type moreRegex: str
        :type stripPrompt: bool
        :rtype: str
        """
        try:

            self._assertInContext()
            self._assertConnectionState(authenticated=True)

        except Exception as ex:

            self._log.error(self._formatException(ex, 'Could not read from the remote host'))
            return ''

        buf = []

        deadline = datetime.utcnow() + timedelta(seconds=timeout)

        self._shell.settimeout(0.1)

        expectingMore = False

        while True:

            try:

                buf.append(self._recv())
                expectingMore = False
                deadline = datetime.utcnow() + timedelta(seconds=timeout)

            except IOError:

                pass

            if not expectingMore:

                lines = buf[-1].splitlines() if len(buf) > 0 else []

                if len(lines) > 0:

                    line = lines[-1]

                    if re.match(moreRegex, line, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                        self._send(' ')
                        expectingMore = True
                        continue

                    if re.match(promptRegex, line, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                        break

            if datetime.utcnow() > deadline:

                break

        self._shell.settimeout(None)

        lines = []

        approximateLineCount = len(''.join(buf).splitlines())

        vt100stream = ByteStream()
        vt100screen = Screen(512, approximateLineCount)
        vt100stream.attach(vt100screen)
        vt100stream.feed(''.join(buf))

        for line in [l.rstrip() for l in vt100screen.display]:

            if stripPrompt and re.match(promptRegex, line, re.MULTILINE | re.IGNORECASE | re.UNICODE):

                continue

            lines.append(line)

        self._readSinceWrite = True

        return '\n'.join(lines).strip('\n')

    def write(self, command, consumeEcho=True):
        """
        :type command: str
        :type consumeEcho: bool
        """
        try:

            self._assertInContext()
            self._assertConnectionState(authenticated=True)

        except Exception as ex:

            self._log.error(self._formatException(ex, 'Could not write to the remote host'))
            return

        command = command.replace('?', '\x16?')

        if not self._readSinceWrite:

            self.read()

        self._readSinceWrite = False

        if not command.endswith('\n'):

            command += '\n'

        self._send(command)

        if not consumeEcho:

            return

        # consume what's echoed back

        readLen = len(command)

        while readLen > 0:

            recvd = self._recv(readLen)
            readLen -= len(recvd)

    def enable(self, password):
        """
        :type password: str
        :rtype: bool
        """
        try:

            self._assertInContext()
            self._assertConnectionState(authenticated=True)

        except Exception as ex:

            self._log.error(self._formatException(ex, 'Could not enable on the remote host'))
            return False

        self.write('enable')

        enableResult = self.read(promptRegex=r'^.*[>#:]\s*$', stripPrompt=False).lower()

        if 'password' not in enableResult:

            self._log.warn('Enable failed: remote did not prompt for a password')
            return False

        self.write(password, consumeEcho=False)

        passwordResult = self.read(promptRegex=r'^.*[>#:]\s*$', stripPrompt=False).lower()

        if 'password' in passwordResult:

            self._log.error('Enable failed: incorrect password')
            return False

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

    def _send(self, value):
        """
        :type value: str
        """
        self._log.debug('SEND: ' + repr(value))
        self._shell.sendall(value)

    def _recv(self, bytes=1024):
        """
        :type bytes: int
        :rtype: str
        """
        result = self._shell.recv(bytes)
        self._log.debug('RECV: ' + repr(result))
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

    def _assertInContext(self):

        if self._client is None:

            raise RuntimeError(
                'The Sisqo.SSH class must be used inside of a context manager (using the "with" statement)')

    def _assertConnectionState(self, connected=None, authenticated=None):
        """
        :type connected: bool|None
        :type authenticated: bool|None
        """
        if not self._client: return  # _assertInContext should handle this case

        transport = self._client.get_transport()
        """:type: paramiko.Transport"""

        if connected == True:

            if transport is None or not transport.is_active():

                raise NotConnectedError('An SSH connection has not been established')

        elif connected == False:

            if transport is not None and transport.is_active():

                raise AlreadyConnectedError('This SSH connection has already been established')

        if authenticated == True:

            if transport is None or not transport.is_authenticated():

                raise NotAuthenticatedError('This SSH connection has not authenticated')

        elif authenticated == False:

            if transport is not None and transport.is_authenticated():

                raise AlreadyAuthenticatedError('This SSH connection has already authenticated')
