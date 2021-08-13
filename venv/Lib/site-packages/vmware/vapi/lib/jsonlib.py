"""
JSON encoder for double values
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import decimal
import json
import math
import six

from vmware.vapi.exception import CoreException
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.l10n.runtime import message_factory

logger = get_vapi_logger(__name__)


def canonicalize_double(obj):
    """
    Canonicalize double based on XML schema double canonical format

    The exponent must be indicated by "E". Leading zeroes and the
    preceding optional "+" sign are prohibited in the exponent. If the
    exponent is zero, it must be indicated by "E0". For the mantissa, the
    preceding optional "+" sign is prohibited and the decimal point is
    required. Leading and trailing zeroes are prohibited subject to the
    following: number representations must be normalized such that there
    is a single digit which is non-zero to the left of the decimal point
    and at least a single digit to the right of the decimal point unless
    the value being represented is zero. The canonical representation
    for zero is 0.0E0
    http://www.w3.org/TR/xmlschema-2/#double

    :type  obj: :class:`decimal.Decimal`
    :param obj: Decimal object to be canonicalized
    :rtype: :class:`str`
    :return: Canonical string representation of the decimal
    """
    # NaN and INF must not be used
    if obj.is_infinite() or obj.is_nan():
        msg = message_factory.get_message(
            'vapi.decimal.canonicalization')
        logger.debug(msg)
        raise CoreException(msg)

    str_val = str(obj)

    # Extract sign of mantissa
    neg_sign = ''
    if str_val.startswith('-'):
        neg_sign = '-'
        str_val = str_val[1:]

    # Extract mantissa and exponent
    mantissa, exponent = None, None
    if 'E' in str_val:
        mantissa, exponent = str_val.split('E')
    else:
        mantissa = str_val

    # decimal class uses context objects that governs precision
    # for arithmetic operations. Setting the precision to the
    # length of mantissa string. To canonicalize the mantissa,
    # we do a division operation, precision maybe lost if we
    # don't set .prec
    decimal.getcontext().prec = len(mantissa)

    mantissa = decimal.Decimal(mantissa)
    exponent = int(exponent) if exponent is not None else 0

    # There MUST be a single non zero digit on the left of the decimal point
    # (unless a zero is represented)
    num_digits = 0
    if mantissa:
        num_digits = int(math.log10(mantissa))
        exponent = exponent + num_digits

        if num_digits < 0:
            # If the number is of the form 0.[0]+[1-9]+
            num_digits *= -1
            # since there MUST be a single non zero digit on the left of decimal
            # point, we have to multiple by an extra 10
            num_digits += 1
            exponent -= 1
            mantissa = mantissa * int(math.pow(10, num_digits))
        else:
            # If the number is of the form [1-9]+.[0-9]+
            mantissa = mantissa / int(math.pow(10, num_digits))

        if mantissa < 1:
            # If the original number is of the form 0.[1-9]+ then, num_digits
            # would have been 0, multile by extra 10 to get it to
            # canonical form
            mantissa *= 10
            exponent -= 1

    # There MUST be at least single digit on the right of the decimal point
    mantissa = str(mantissa)
    if '.' not in mantissa:
        mantissa = '%s.0' % mantissa

    # If there are any trailing zeros, strip them off
    left, right = mantissa.split('.')
    first = right[0]
    remaining = right[1:].rstrip('0')
    mantissa = '%s.%s%s' % (left, first, remaining)

    return '%s%sE%s' % (neg_sign, mantissa, exponent)


class DecimalEncoder(json.JSONEncoder):
    """
    Class that adds capability of encoding decimal
    in JSON
    """
    # In 2.x version of json library, _iterencode should be overriden
    # to have special encoding for objects
    def _iterencode(self, obj, markers=None):
        """
        Overriding the decimal encoding for the default encoder
        """
        if isinstance(obj, decimal.Decimal):
            return (six.text_type(obj) for obj in [obj])
        return super(DecimalEncoder, self)._iterencode(obj, markers)  # pylint: disable=W0212

    # In 3.x version of json library, default() should be overrriden
    # to have special encoding for objects
    def default(self, obj):  # pylint: disable=E0202
        if isinstance(obj, decimal.Decimal):
            return (six.text_type(obj) for obj in [obj])
        return json.JSONEncoder.default(self, obj)
