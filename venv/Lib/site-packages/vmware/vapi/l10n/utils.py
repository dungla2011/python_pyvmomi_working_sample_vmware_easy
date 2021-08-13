"""
Utility methods for l10n support
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import re

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class LocalizationHeaderParser(object):
    """
    Helper class for parsing of localization related headers
    """

    # RFC 7230 Section 3.2.3 "Whitespace"
    # ows            = *( SP / HTAB )
    #                ; optional whitespace
    _ows = "[ \t]*"

    # RFC 7231 Section 5.3.1 "Quality Values"
    # qvalue = ( "0" [ "." 0*3DIGIT ] )
    #        / ( "1" [ "." 0*3("0") ] )
    _qvalue = r"(?:0(?:\.[0-9]{0,3})?)" "|" r"(?:1(?:\.0{0,3})?)"
    # weight = ows ";" ows "q=" qvalue
    _weight = _ows + ";" + _ows + "[qQ]=(" + _qvalue + ")"

    # RFC 7231 Section 5.3.5 "Accept-Language":
    # Accept-Language = 1#( language-range [ weight ] )
    # language-range  =
    #           <language-range, see [RFC4647], Section 2.1>
    # RFC 4647 Section 2.1 "Basic Language Range":
    # language-range   = (1*8ALPHA *("-" 1*8alphanum)) / "*"
    # alphanum         = ALPHA / DIGIT
    _lang_range = r"\*|" "(?:" "[A-Za-z]{1,8}" "(?:-[A-Za-z0-9]{1,8})*" ")"
    _lang_range_and_weight = "(" + _lang_range + ")(?:" + _weight + ")?"
    _list_lang_range_and_weight = ("^(?:," + _ows + ")*"
                                   + _lang_range_and_weight
                                   + "(?:" + _ows + ",(?:"
                                   + _ows + _lang_range_and_weight
                                   + ")?)*$")
    locale_regex = re.compile(_lang_range_and_weight)
    locale_validation_regex = re.compile(_list_lang_range_and_weight)

    @classmethod
    def parse_locale_header(cls, header):
        """
        Parse the locale headers - 'accept-language' and 'format-locale'
        """
        if cls.locale_validation_regex.match(header) is None:
            raise Exception('Invalid accept language header')

        lang_ranges = []
        for match in cls.locale_regex.finditer(header):
            lang_range = match.group(1)
            qvalue = match.group(2)
            qvalue = float(qvalue) if qvalue else 1.0
            lang_ranges.append((lang_range, qvalue))

        return lang_ranges
