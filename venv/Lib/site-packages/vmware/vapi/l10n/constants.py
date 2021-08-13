"""
Constants for localization
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import sys

#
# There is no standard string that can be used across platforms
# to specify english locale. So, based on the platform, we are setting it
# to the english locale string for that platform.
#
# Worst case if we don't have information for that platform, then we are
# defaulting to '' which will set locale to default locale for that
# environment. In that case, the messages generated might not be US english
# complaint.
#
platform_default_en_locales = {
    'win32': 'us_US',
    'linux2': 'en_US.utf8',
    'darwin': 'en_US'
}
# If the platform is not found, then return ''
DEFAULT_LOCALE = platform_default_en_locales.get(sys.platform, '')
