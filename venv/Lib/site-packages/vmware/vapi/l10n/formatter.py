"""
Helper classes for formatting the message for localization
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import locale
import re
import six
from datetime import datetime

from vmware.vapi.message import MessageFormatter


class StringFormatter(MessageFormatter):
    """
    Format the string
    """
    # This regex is used to split the message template into tokens
    # Same as the below, but all the groups are matching but non-capturing
    string_template = re.compile(
        '(%(?:\\d+\\$)?(?:[-#+ 0,(\\<]*)(?:\\d+)?(?:\\.\\d+)?(?:[tT])?'
        '(?:[a-zA-Z]))'
    )

    # This is used to split a format specifier into groups
    # %[argument_index$][flags][width][.precision][t]conversion
    format_specifier = re.compile(
        '%(\\d+\\$)?([-#+ 0,(\\<]*)(\\d+)?(\\.\\d+)?([tT])?([a-zA-Z])')

    @classmethod
    def _localize_datetime(cls, datetime_arg):
        """
        Localize a datetime object

        :type  datetime_arg: :class:`datetime.datetime`
        :param datetime_arg: Datetime object
        :rtype: :class:`str`
        :return: Localized datetime string
        """
        # Importing DateTimeConverter here to avoid circular dependency
        from vmware.vapi.bindings.datetime_helper import DateTimeConverter
        if isinstance(datetime_arg, six.string_types):
            datetime_arg = DateTimeConverter.convert_to_datetime(datetime_arg)
        if not isinstance(datetime_arg, datetime):
            raise TypeError('Argument is not a datetime')
        # XXX: strftime does not handle dates before 1900
        return datetime_arg.strftime(locale.nl_langinfo(locale.D_T_FMT)).strip()

    @classmethod
    def _localize_element(cls, format_specifier, argument, grouping=False):
        """
        Localize one of the arguments in localizable message

        :type  format_specifier: :class:`str`
        :param format_specifier: Format specifier for the argument
        :type  argument: :class:`object`
        :param argument: Argument to be localized
        :type  grouping: :class:`bool`
        :param grouping: Indicates whether to use thousands seperater or not.
        :rtype: :class:`str`
        :return: Localized string
        """
        if format_specifier.endswith('d'):
            if six.PY2:
                argument = long(argument)
            else:
                argument = int(argument)
        elif format_specifier.endswith('f'):
            argument = float(argument)
        return locale.format_string(format_specifier, argument, grouping)

    @classmethod
    def _localize_string(cls, tokens, args):
        """
        Localize the given string

        :type  tokens: :class:`list` of :class:`str`
        :param tokens: Tokens from the message template
        :type  args: :class:`list` of :class:`object`
        :param args: Arguments for the message template
        :rtype: :class:`str`
        :return: Localized message
        """
        result = []
        arg_index = 0
        for token in tokens:
            match = cls.format_specifier.match(token)
            if match:
                if match.groups()[4]:
                    dt_arg = args[arg_index]
                    result.append(cls._localize_datetime(dt_arg))
                elif match.groups()[1] == ',':
                    # remove ',' flag from the token
                    groups = match.groups()
                    groups = groups[0:1] + groups[2:]
                    token = ''.join([elem for elem in groups
                                     if elem])
                    token = '%' + token
                    result.append(
                        cls._localize_element(token,
                                              args[arg_index],
                                              grouping=True))
                else:
                    result.append(
                        cls._localize_element(token,
                                              args[arg_index]))
                arg_index += 1
            else:
                result.append(token)

        return ''.join(result)

    @classmethod
    def format_msg(cls, msg, args):
        """
        Format the string

        :type  msg: :class:`str`
        :param msg: Message template
        :type  args: :class:`list` of :class:`object`
        :param args: Arguments for the message
        :rtype: :class:`str`
        :return: Localized message
        """
        msg_tokens = cls.string_template.split(msg)

        modified_msg_tokens = []
        argument_indexes = []
        for idx, token in enumerate(msg_tokens):
            match = cls.format_specifier.match(token)
            if match:
                # Check for argument index
                argument_index = match.groups()[0]
                if argument_index:
                    # Extract argument index
                    argument_indexes.append(
                        argument_index.split('$')[0])

                    # Remove argument index from format specifier
                token = ''.join([elem for elem in match.groups()[1:]
                                 if elem])
                modified_msg_tokens.append('%' + token)
            else:
                modified_msg_tokens.append(token)
        tokens = modified_msg_tokens

        if argument_indexes:
            if len(argument_indexes) != len(args):
                raise TypeError('Number of argument index specifiers '
                                'do not match number of arguments')
            # Rearrange the arguments
            args = [args[int(idx) - 1] for idx in argument_indexes]

        return cls._localize_string(tokens, args)
