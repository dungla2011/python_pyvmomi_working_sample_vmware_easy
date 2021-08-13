"""
Fingerprint related functions
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2020 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import binascii
import six


def generate_fingerprint(data):
    """
    Generate fingerprint for the given data

    :rtype: :class:`str`
    :return: fingerprint of the given data
    """
    if six.PY3:
        if isinstance(data, six.string_types):
            data = data.encode('utf-8')
    # bitwise operation is needed for Python 2.x to give unsigned result
    # see documentation here: https://docs.python.org/3/library/binascii.html#binascii.crc32
    return '{:08x}'.format(binascii.crc32(data) & 0xffffffff)
