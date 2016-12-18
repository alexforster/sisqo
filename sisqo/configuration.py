# -*- coding: UTF-8 -*-
#
# Copyright © 2017 Alex Forster. All rights reserved.
# This software is licensed under the 3-Clause ("New") BSD license.
# See the LICENSE file for details.
#


import re


class Line:

    def __init__(self, lineNumber, indent, value):
        """
        :type number: int
        :type indent: str
        :type value: str
        """
        self._lineNumber = int(lineNumber) if lineNumber else None

        self._indent = str(indent) if indent else ''

        self._value = str(value) if value else None

        self.parent = None

        self.children = []

    def __iter__(self):

        return iter(self.children)

    def _flatten(self):
        """
        :rtype: list[str]
        """
        result = [('  ' * self.depth) + self._value]

        for child in self.children:

            if len(child.children) > 0:

                result += child._flatten()

            else:

                result += [('  ' * child.depth) + child.value]

        return result

    def __str__(self):
        """
        :rtype: str
        """
        return '\r\n'.join(self._flatten())

    def __repr__(self):
        """
        :rtype: str
        """
        return '<{}>'.format(self.value)

    @property
    def value(self):
        """
        :rtype: str
        """
        return self._value

    @property
    def lineNumber(self):
        """
        :rtype: int
        """
        return self._lineNumber

    @property
    def indentation(self):
        """
        :rtype: int
        """
        return len(self._indent)

    @property
    def depth(self):
        """
        :rtype: int
        """
        result = 0
        current = self

        while current.parent is not None:

            result += 1
            current = current.parent

        return result

    def findChild(self, regex):
        """
        :type regex: str
        :rtype: Line|None
        """
        for child in self.children:

            if re.match(regex, child.value, flags=re.IGNORECASE | re.UNICODE):

                return child

        return None

    def findChildren(self, regex):
        """
        :type regex: str
        :rtype: list[Line]|None
        """
        result = []

        for child in self.children:

            if re.match(regex, child.value, flags=re.IGNORECASE | re.UNICODE):

                result.append(child)

        return result


class Configuration:

    def __init__(self, configString):
        """
        :type configString: str
        """
        self._root = []
        self._parserStack = []

        configString = str(configString) if configString else None

        if configString is None: return

        self._parse(configString)

    def __iter__(self):

        return iter(self._root)

    def _flatten(self):
        """
        :rtype: list[str]
        """
        result = []

        for child in self._root:

            result += child._flatten()

        return result

    def __str__(self):
        """
        :rtype: str
        """
        return '\r\n'.join(self._flatten())

    def __repr__(self):
        """
        :rtype: str
        """
        return '<type Configuration>'

    def findChild(self, regex):
        """
        :type regex: str
        :rtype: Line|None
        """
        for child in self._root:

            if re.match(regex, child.value, flags=re.IGNORECASE | re.UNICODE):

                return child

        return None

    def findChildren(self, regex):
        """
        :type regex: str
        :rtype: list[Line]|None
        """
        result = []

        for child in self._root:

            if re.match(regex, child.value, flags=re.IGNORECASE | re.UNICODE):

                result.append(child)

        return result

    def _parse(self, configString):
        """
        :type configString: str
        """
        if configString is None: return

        # split the config by newlines
        config = re.split(r'\r?\n', configString, flags=re.UNICODE)

        # remove empty or all-whitespace lines
        config = [line for line in config if len(line.strip()) > 0]

        # skip lines until the first comment
        for i, line in enumerate(config[:]):

            if line.startswith('!'):

                config = config[i:]
                break

        # parse remaining config lines
        for i, line in enumerate(config):

            self._parseLine(configLine=line, lineNumber=i)

    def _parseLine(self, configLine, lineNumber):
        """
        :type configLine: str
        :type lineNumber: int
        """
        # construct a strong representation of this line...

        line = Line(
            lineNumber=lineNumber,
            indent=configLine[:len(configLine) - len(configLine.lstrip(' '))],
            value=configLine.strip())

        # track this line's parent-child relationship to the previous line(s) using _parserStack...

        # if indentation has been reduced from the previous line...
        if len(self._parserStack) > 0 and line.indentation < self._parserStack[-1].indentation:

            # walk the stack
            for _ in range(len(self._parserStack)):

                # unconditionally pop an element, since its indentation should always be less than or equal to our current indentation
                self._parserStack.pop()

                # if we've found an entry on the stack that matches the indentation level we're looking for, stop
                if line.indentation == self._parserStack[-1].indentation:

                    break

                # die if we find indentation that breaks the hierarchical nature of the structure
                if line.indentation > self._parserStack[-1].indentation:

                    raise Exception('Improperly aligned indentation')

        # if the current indentation matches the indentation of the child at the top of the stack...
        if len(self._parserStack) > 0 and line.indentation == self._parserStack[-1].indentation:

            self._parserStack.pop()

        # drop the line if it's a comment; at this point we've already accounted for the line's indentation
        if configLine.lstrip().startswith('!'):

            return

        # set this line's parent line
        line.parent = self._parserStack[-1] if len(self._parserStack) > 0 else None

        # create a list of child lines
        self._parserStack.append(line)

        if line.parent is not None:

            line.parent.children.append(line)  # add this line to its parent

        else:

            self._root.append(line)  # add this line as a root line
