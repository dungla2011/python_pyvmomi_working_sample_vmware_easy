"""
Utility library for converting to/from datetime objects in Python Bindings
"""
__author__ = 'VMware, Inc'
__copyright__ = 'Copyright 2015, 2017, 2020 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import datetime
import re
import six

from vmware.vapi.exception import CoreException
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class DateTimeConverter(object):
    """
    Helper class to convert to/from Python datetime strings to
    datetime objects.

    Datetime values are transported as a string values that have to be
    converted to Python datetime object for use in Python bindings. The
    string value is in RFC 3339 format (https://tools.ietf.org/html/rfc3339).

    The grammar for regex is as follows:

    date-time       = full-date "T" full-time
    full-date       = date-fullyear "-" date-month "-" date-mday
    date-fullyear   = 4DIGIT
    date-month      = 2DIGIT  ; 01-12
    date-mday       = 2DIGIT  ; 01-28, 01-29, 01-30, 01-31 based on month/year
    full-time       = partial-time time-offset
    partial-time    = time-hour ":" time-minute ":" time-second
        [time-sub-second]
    time-hour       = 2DIGIT  ; 00-23
    time-minute     = 2DIGIT  ; 00-59
    time-second     = 2DIGIT  ; 00-58, 00-59, 00-60 based on leap second rules
    time-sub-second    = "." time-secfrac
    time-secfrac    = 1*DIGIT
    time-offset     = "Z" / time-numoffset
    time-numoffset  = ("+" / "-") time-hour ":" time-minute
    group(1) = full-date
    group(2) = date-fullyear
    group(3) = date-month
    group(4) = date-mday
    group(5) = full-time
    group(6) = partial-time
    group(7) = time-hour
    group(8) = time-minute
    group(9) = time-second
    group(10) = time-sub-second
    group(11) = time-secfrac
    group(12) = time-offset
    group(13) = time-numoffset
    group(14) = time-hour
    group(15) = time-minute
    """
    _rfc3339_dt_pattern = \
        '^((\\d{4})-(\\d{2})-(\\d{2}))T(((\\d{2}):(\\d{2}):(\\d{2})' \
        '(\\.(\\d+))?)(Z|([\\+\\-](\\d{2}):(\\d{2}))))$'
    _rfc3339_dt_expr = re.compile(_rfc3339_dt_pattern)

    @staticmethod
    def convert_to_datetime(datetime_str):
        """
        Parse RFC 3339 date time from string.

        :type  datetime_str: :class:`str`
        :param datetime_str: Datetime in string representation that is in
                             RFC 3339 format
        :rtype: :class:`datetime.datetime`
        :return: Datetime object
        """
        datetime_val = DateTimeConverter.convert_from_rfc3339_to_datetime(datetime_str)
        return datetime_val

    @staticmethod
    def convert_from_rfc3339_to_datetime(datetime_str):
        """
        Parse RFC 3339 date time from string.

        :type  datetime_str: :class:`str`
        :param datetime_str: Datetime in string representation that is in
            RFC 3339 format
        :rtype: :class:`datetime.datetime`
        :return: Datetime object
        """
        datetime_val = None
        match = DateTimeConverter._rfc3339_dt_expr.match(datetime_str)
        if not match:
            DateTimeConverter._process_error(
                'vapi.bindings.typeconverter.datetime.deserialize.invalid'
                '.format',
                datetime_str, DateTimeConverter._rfc3339_dt_pattern)

        year = int(match.group(2))
        month = int(match.group(3))
        if month < 1 or month > 12:
            DateTimeConverter._process_error(
                'vapi.bindings.typeconverter.datetime.deserialize.month'
                '.invalid',
                datetime_str)

        day = int(match.group(4))
        if day < 1 or day > 31:
            DateTimeConverter._process_error(
                'vapi.bindings.typeconverter.datetime.deserialize.day.invalid',
                datetime_str)

        hour = int(match.group(7))
        if hour > 23:
            DateTimeConverter._process_error(
                'vapi.bindings.typeconverter.datetime.deserialize.hour.invalid',
                datetime_str)

        minute = int(match.group(8))
        if minute > 59:
            DateTimeConverter._process_error(
                'vapi.bindings.typeconverter.datetime.deserialize.minute'
                '.invalid',
                datetime_str)

        second = int(match.group(9))
        if second > 59:
            DateTimeConverter._process_error(
                'vapi.bindings.typeconverter.datetime.deserialize.second'
                '.invalid',
                datetime_str)

        microsecond = int('{}000000'.format(match.group(11))[:6]) \
            if match.group(11) else 0
        if match.group(14):
            timedelta = datetime.timedelta(
                hours=int(match.group(14)), minutes=int(match.group(15)))
            if match.group(13).startswith('-'):
                timedelta = -timedelta
            tzinfo = DateTimeConverter._get_tzinfo(timedelta)
        else:
            tzinfo = None
        try:
            datetime_val = datetime.datetime(
                year=year, month=month, day=day, hour=hour, minute=minute,
                second=second, microsecond=microsecond, tzinfo=tzinfo)
        except Exception as err:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.datetime.deserialize.invalid.time',
                datetime_str, str(err))
            logger.error(msg)
            raise CoreException(msg)

        return datetime_val

    @staticmethod
    def _get_tzinfo(timedelta):
        """
        Get the TZInfo from the sepcified time difference from UTC

        :type  timedelta: :class:`datetime.timedelta`
        :param timedelta: The time difference from UTC
        :rtype:  :class:`datetime.tzinfo`
        :return: The TZInfo corresponding to the time delta
        """
        if six.PY2:
            class GenericTZInfo(datetime.tzinfo):
                """
                Class representing tzinfo for any time zone specified by the
                timedelta.
                """
                def __init__(self, timedelta):
                    self.timedelta = timedelta

                def utcoffset(self, dt):
                    return self.timedelta

                def dst(self, dt):
                    return self.timedelta

                def tzname(self):
                    return None

            return GenericTZInfo(timedelta)
        else:
            return datetime.timezone(timedelta)

    @staticmethod
    def convert_from_datetime(datetime_obj):
        """
        Convert from Python native datetime object to the datetime format in
        vAPI Runtime i.e. YYYY-MM-DDThh:mm:ss.sssZ.

        datetime objects returned by datetime.now() or datetime.utcnow() does
        not contain any timezone information. The caller to this method should
        only pass datetime objects that have time in UTC timezone.

        datetime objects have microsecond precision but the vAPI datetime
        string format has millisecond precision. The method will truncate the
        microsecond to millisecond and won't do any rounding of the value.

        :type  datetime_obj: :class:`datetime.datetime`
        :param datetime_obj: Datetime object with UTC time
        :rtype: :class:`str`
        :return: String representation of the input datetime object
        """
        if datetime_obj.tzinfo:
            # If tzinfo object is present, it should be in UTC timezone
            # i.e. timedelta is 0
            if datetime_obj.tzinfo.utcoffset(datetime_obj) != \
                    datetime.timedelta(0):
                msg = message_factory.get_message(
                    'vapi.bindings.typeconverter.datetime.serialize.invalid.tz',
                    str(datetime_obj))
                logger.error(msg)
                raise CoreException(msg)

        # Since it is UTC timezone, replacing it with None
        # the output of isoformat() does not match vAPI runtime datetime string
        # format if tzinfo is present in the datetime object
        datetime_obj = datetime_obj.replace(tzinfo=None)

        iso_str = datetime_obj.isoformat()
        if datetime_obj.microsecond:
            # datetime prints microseconds, reducing precision to milliseconds
            iso_str = iso_str[:-3]
        else:
            # Python .isoformat does not print microsecond if it is 0
            iso_str = '%s.000' % iso_str
        return '%sZ' % iso_str  # Adding Z to indicate it is UTC timezone

    @staticmethod
    def _process_error(msg_id, *args):
        """
        Helper method to process error condition. It creates a localizable
        message, logs it in debug mode and raises a CoreException.

        :type  msg_id: :class:`str`
        :param msg_id: The unique message identifier
        :type  args: :class:`list` of :class:`object`
        :param args: Arguments for the message
        :raise CoreException: Raise the CoreException with the localizable
            message
        """
        msg = message_factory.get_message(msg_id, *args)
        logger.debug(msg)
        raise CoreException(msg)

utc_tzinfo = None
if six.PY2:
    class UTC(datetime.tzinfo):
        """
        tzinfo class for UTC timezone
        """
        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def tzname(self, dt):
            return 'UTC'

        def dst(self, dt):
            return datetime.timedelta(0)

    utc_tzinfo = UTC()
else:
    utc_tzinfo = datetime.timezone.utc


def convert_to_utc(date_time):
    """
    Convert a given datetime object to UTC timezone
    """
    if date_time:
        return date_time.astimezone(utc_tzinfo)
