"""
Helper classes for internationalization of the messages for static bindings
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import decimal
import six
from datetime import datetime

from vmware.vapi.bindings.datetime_helper import DateTimeConverter
from vmware.vapi.lib.log import get_vapi_logger


logger = get_vapi_logger(__name__)


class MessageArgumentConverter(object):
    """
    Utility class for converting localizable message arguments to strings
    """
    @staticmethod
    def to_string(args):
        """
        Convert argument list to string argument list

        :type  args: :class:`list` of :class:`object`
        :param args: List of arguments
        :rtype: :class:`list` of :class:`str`
        :return: List of string arguments
        """
        result = []
        for arg in args:
            if isinstance(arg, datetime):
                result.append(
                    DateTimeConverter.convert_from_datetime(arg))
            elif (isinstance(arg, six.string_types) or
                    isinstance(arg, six.integer_types) or
                    isinstance(arg, decimal.Decimal)):
                result.append(str(arg))
            else:
                raise TypeError('Unsupported type for message argument: %s',
                                type(arg).__name__)
        return result
