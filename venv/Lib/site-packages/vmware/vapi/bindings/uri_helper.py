"""
Utility library for validating IRI that conform to RFC 3987
"""
__author__ = 'VMware, Inc'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import re
import ast

from vmware.vapi.exception import CoreException
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class URIValidator(object):
    """
    Helper class for validation of IRI's
    """
    # The regex is taken from RFC 3987 (IRI)
    # Note 1: RFC 3987 (IRI) uses HEXDIG
    #         HEXDIG is specified in RFC 2234 is [0-9][A-F]
    #         RFC 2396 allows HEXDIG to be [0-9][A-F][a-f]
    #         So, in this regex, HEXDIG uses the RFC 2396 standard
    _rules = (
        ('IRI_reference', r"(?:{IRI}|{irelative_ref})"),
        ('IRI', r"{absolute_IRI}(?:\#{ifragment})?"),
        ('absolute_IRI', r"{scheme}:{ihier_part}(?:\?{iquery})?"),
        ('irelative_ref', (r"(?:{irelative_part}"
                           r"(?:\?{iquery})?(?:\#{ifragment})?)")),
        ('ihier_part', (r"(?://{iauthority}{ipath_abempty}"
                        r"|{ipath_absolute}|{ipath_rootless}|{ipath_empty})")),
        ('irelative_part', (r"(?://{iauthority}{ipath_abempty}"
                            r"|{ipath_absolute}|{ipath_noscheme}|{ipath_empty})")),
        ('iauthority', r"(?:{iuserinfo}@)?{ihost}(?::{port})?"),
        ('iuserinfo', r"(?:{iunreserved}|{pct_encoded}|{sub_delims}|:)*"),
        ('ihost', r"(?:{IP_literal}|{IPv4address}|{ireg_name})"),

        ('ireg_name', r"(?:{iunreserved}|{pct_encoded}|{sub_delims})*"),
        ('ipath', (r"(?:{ipath_abempty}|{ipath_absolute}|{ipath_noscheme}"
                   r"|{ipath_rootless}|{ipath_empty})")),
        ('ipath_empty', r""),
        ('ipath_rootless', r"{isegment_nz}(?:/{isegment})*"),
        ('ipath_noscheme', r"{isegment_nz_nc}(?:/{isegment})*"),
        ('ipath_absolute', r"/(?:{isegment_nz}(?:/{isegment})*)?"),
        ('ipath_abempty', r"(?:/{isegment})*"),
        ('isegment_nz_nc', r"(?:{iunreserved}|{pct_encoded}|{sub_delims}|@)+"),
        ('isegment_nz', r"{ipchar}+"),
        ('isegment', r"{ipchar}*"),
        ('iquery', r"(?:{ipchar}|{iprivate}|/|\?)*"),
        ('ifragment', r"(?:{ipchar}|/|\?)*"),
        ('ipchar', r"(?:{iunreserved}|{pct_encoded}|{sub_delims}|:|@)"),
        ('iunreserved', r"(?:[a-zA-Z0-9._~-]|{ucschar})"),
        ('iprivate', r"[\uE000-\uF8FF]"),
        ('ucschar', (r"[\xA0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]")),
        ('scheme', r"[a-zA-Z][a-zA-Z0-9+.-]*"),
        ('port', r"[0-9]*"),
        ('IP_literal', r"\[(?:{IPv6address}|{IPvFuture})\]"),
        ('IPv6address', (r"(?:                             (?:{h16}:){{6}} {ls32}"
                         r"|                            :: (?:{h16}:){{5}} {ls32}"
                         r"|                    {h16}?  :: (?:{h16}:){{4}} {ls32}"
                         r"| (?:(?:{h16}:)?     {h16})? :: (?:{h16}:){{3}} {ls32}"
                         r"| (?:(?:{h16}:){{,2}}{h16})? :: (?:{h16}:){{2}} {ls32}"
                         r"| (?:(?:{h16}:){{,3}}{h16})? :: (?:{h16}:)      {ls32}"
                         r"| (?:(?:{h16}:){{,4}}{h16})? ::                 {ls32}"
                         r"| (?:(?:{h16}:){{,5}}{h16})? ::                 {h16} "
                         r"| (?:(?:{h16}:){{,6}}{h16})? ::                      )"
                         ).replace(' ', '')),
        ('ls32', r"(?:{h16}:{h16}|{IPv4address})"),
        ('h16', r"[0-9A-Fa-f]{{1,4}}"),
        ('IPv4address', r"(?:{dec_octet}\.){{3}}{dec_octet}"),
        ('dec_octet', r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"),
        ('IPvFuture', r"v[0-9A-Fa-f]+\.(?:{unreserved}|{sub_delims}|:)+"),
        ('unreserved', r"[a-zA-Z0-9_.~-]"),
        ('reserved', r"(?:{gen_delims}|{sub_delims})"),
        ('pct_encoded', r"%[0-9A-Fa-f][0-9A-Fa-f]"),
        ('gen_delims', r"[:/?#[\]@]"),
        ('sub_delims', r"[!$&'()*+,;=]"),
    )
    # Use a dictionary to save the compiled regexs
    compiled_regex = {}

    # Just compute the regex for IRI's now.
    for rule_type in ['IRI', 'IRI_reference']:
        regex = compiled_regex.get(rule_type)
        if regex is None:
            final_regex = {}
            for key, value in reversed(_rules):
                final_regex[key] = value.format(**final_regex)

            regex_str = ''.join(['^%(', rule_type, ')s$'])
            regex_str = regex_str % final_regex

            # ``\u`` and ``\U`` escapes must be preprocessed
            # http://bugs.python.org/issue3665
            unicode_wrap = 'u"""{0}"""'
            regex_str = ast.literal_eval(unicode_wrap.format(regex_str))

            regex = re.compile(regex_str)
            compiled_regex[rule_type] = regex
    del _rules

    @staticmethod
    def validate(iri):
        """
        Validate the given IRI string

        :type  iri: :class:`str`
        :param iri: IRI string to be validated
        """
        # Input could be an absolute or relative IRI string, validate
        # it against both of them
        match = None
        for iri_type in ['IRI', 'IRI_reference']:
            regex = URIValidator.compiled_regex.get(iri_type)
            match = regex.match(iri)
            if match is not None:
                break
        else:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.uri.invalid.format',
                repr(iri))
            logger.debug(msg)
            raise CoreException(msg)
