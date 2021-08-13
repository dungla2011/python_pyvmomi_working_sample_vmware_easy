# -*- coding: utf-8 -*-

"""
SSO Security Helper
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from base64 import b64encode, b64decode
import datetime
import decimal
import json
from OpenSSL import crypto
import re
import six

from vmware.vapi.bindings.datetime_helper import DateTimeConverter
from vmware.vapi.core import SecurityContext
from vmware.vapi.lib.jsonlib import (
    DecimalEncoder, canonicalize_double)
from vmware.vapi.lib.constants import (
    PARAMS, SCHEME_ID, EXECUTION_CONTEXT, SECURITY_CONTEXT)
from vmware.vapi.protocol.common.lib import RequestProcessor

key_regex = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----\n')
SAML_SCHEME_ID = 'com.vmware.vapi.std.security.saml_hok_token'
SAML_BEARER_SCHEME_ID = 'com.vmware.vapi.std.security.saml_bearer_token'
PRIVATE_KEY = 'privateKey'
SAML_TOKEN = 'samlToken'
SIGNATURE_ALGORITHM = 'signatureAlgorithm'
DEFAULT_ALGORITHM_TYPE = 'RS256'
TIMESTAMP = 'timestamp'
EXPIRES = 'expires'
CREATED = 'created'
REQUEST_VALIDITY = 20
SIGNATURE = 'signature'
DIGEST = 'value'
AUTHENTICATED = 'requestAuthenticated'
STS_URL_PROP = 'stsurl'
CERTIFICATE_PROP = 'certificate'
PRIVATE_KEY_PROP = 'privatekey'
CERT_NS = '{http://www.w3.org/2000/09/xmldsig#}'
SECTION = __name__
# Algorithm Header Parameter Values for JWS based on the following link
# https://datatracker.ietf.org/doc/draft-ietf-jose-json-web-algorithms/?include_text=1
algorithm_map = {
    'RS256': 'sha256',
    'RS384': 'sha384',
    'RS512': 'sha512',
}


def create_saml_bearer_security_context(token):
    """
    Create a security context for SAML bearer token based
    authentication scheme

    :type  token: :class:`str`
    :param token: SAML Token
    """
    return SecurityContext({SCHEME_ID: SAML_BEARER_SCHEME_ID,
                            SAML_TOKEN: token})


def create_saml_security_context(token, private_key):
    """
    Create a security context for SAML token based
    authentication scheme

    :type  token: :class:`str`
    :param token: SAML Token
    :type  private_key: :class:`str`
    :param private_key: Absolute file path of the private key of the user
    :rtype: :class:`vmware.vapi.core.SecurityContext`
    :return: Newly created security context
    """
    private_key_data = None
    with open(private_key, 'r') as fp:
        private_key_data = fp.read()
    return SecurityContext({SCHEME_ID: SAML_SCHEME_ID,
                            PRIVATE_KEY: private_key_data,
                            SAML_TOKEN: token,
                            SIGNATURE_ALGORITHM: DEFAULT_ALGORITHM_TYPE})


class JSONCanonicalEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder class to canonicalize dictionary
    and list objects
    """
    def encode(self, o):
        """
        Encode a given python object

        :type  o: :class:`object`
        :param o: Python object
        :rtype: :class:`str`
        :return: JSON string in canonicalized form
        """
        if isinstance(o, dict):
            # Remove non-significant whitespace characters
            # Keys are sorted lexicographically using UCS code
            # point values
            sorted_keys = sorted(o.keys())
            sorted_items = ['%s:%s' % (self.encode(key),
                                       self.encode(o[key]))
                            for key in sorted_keys]
            string = ','.join(sorted_items)
            return '{%s}' % string
        elif isinstance(o, list):
            # Arrays must preserve the initial ordering
            # Remove non-significant whitespace characters
            string = ','.join([self.encode(item)
                               for item in o])
            return '[%s]' % string
        elif isinstance(o, decimal.Decimal):
            return canonicalize_double(o)
        else:
            return json.JSONEncoder.encode(self, o)


class JSONCanonicalizer(object):
    """
    This class is responsible for transforming JSON messages into their
    canonical representation.

    The canonical form is defined by the following rules:
        1. Non-significant(1) whitespace characters MUST NOT be used
        2. Non-significant(1) line endings MUST NOT be used
        3. Entries (set of name/value pairs) in JSON objects MUST be sorted
           lexicographically(2) by their names based on UCS codepoint values
        4. Arrays MUST preserve their initial ordering

    Link to the IEFT proposal:
    https://datatracker.ietf.org/doc/draft-staykov-hu-json-canonical-form/
    """
    @staticmethod
    def canonicalize(input_message):
        """
        Canonicalize the input message

        :type  input_message: :class:`str`
        :param input_message: Input message
        :rtype: :class:`str`
        :return: Canonicalized message
        """
        py_obj = json.loads(input_message, parse_float=decimal.Decimal)
        return JSONCanonicalEncoder().encode(py_obj)

    @staticmethod
    def canonicalize_py_obj(py_obj):
        """
        Canonicalize the input python object

        :type  input_message: :class:`object`
        :param input_message: Input python object
        :rtype: :class:`str`
        :return: Canonicalized message
        """
        return JSONCanonicalEncoder().encode(py_obj)


class JSONSSOSigner(RequestProcessor):
    """
    This class is used for signing JSON request messages
    """
    def process(self, input_message):
        """
        Sign the input JSON request message.

        The message is signed using user's private key. The digest and saml
        token is then added to the security context block of the execution
        context. A timestamp is also added to guard against replay attacks

        Sample input security context:
        {
            'schemeId': 'SAML_TOKEN',
            'privateKey': <PRIVATE_KEY>,
            'samlToken': <SAML_TOKEN>,
            'signatureAlgorithm': <ALGORITHM>,
        }

        Security context block before signing:
        {
            'schemeId': 'SAML_TOKEN',
            'signatureAlgorithm': <ALGORITHM>,
            'timestamp': {
                'created': '2012-10-26T12:24:18.941Z',
                'expires': '2012-10-26T12:44:18.941Z',
            }
        }

        Security context block after signing:
        {
            'schemeId': 'SAML_TOKEN',
            'signatureAlgorithm': <ALGORITHM>,
            'signature': {
                'samlToken': <SAML_TOKEN>,
                'value': <DIGEST>
            }
            'timestamp': {
                'created': '2012-10-26T12:24:18.941Z',
                'expires': '2012-10-26T12:44:18.941Z',
            }
        }
        """
        if input_message is None:
            return None

        # process only if the schemeId in the request matches the schemeId of
        # this signer
        if isinstance(input_message, six.binary_type):
            unicode_input_message = input_message.decode()
        else:
            unicode_input_message = input_message
        if SAML_SCHEME_ID not in unicode_input_message:
            return input_message

        py_obj = json.loads(unicode_input_message, parse_float=decimal.Decimal)
        json_params = py_obj.get(PARAMS)  # pylint: disable=E1103
        ctx = json_params.get(EXECUTION_CONTEXT)

        sec_ctx = ctx.get(SECURITY_CONTEXT)
        private_key = sec_ctx.get(PRIVATE_KEY)
        saml_token = sec_ctx.get(SAML_TOKEN)
        jws_algorithm = sec_ctx.get(SIGNATURE_ALGORITHM)
        algorithm = algorithm_map.get(jws_algorithm)

        new_sec_ctx = {}
        new_sec_ctx[SCHEME_ID] = sec_ctx.get(SCHEME_ID)
        new_sec_ctx[TIMESTAMP] = _generate_request_timestamp()
        new_sec_ctx[SIGNATURE_ALGORITHM] = jws_algorithm

        # Replace the old security context with the new one
        del ctx[SECURITY_CONTEXT]
        ctx[SECURITY_CONTEXT] = new_sec_ctx

        pkey = crypto.load_privatekey(
            crypto.FILETYPE_PEM, _prep_private_key(private_key))
        canonical_message = JSONCanonicalizer.canonicalize_py_obj(py_obj)
        base64_encoded_digest = b64encode(crypto.sign(
            pkey, canonical_message.encode(), algorithm))
        # Convert to unicode since json library does not accept bytes
        unicode_digest = base64_encoded_digest.decode()

        new_sec_ctx[SIGNATURE] = {SAML_TOKEN: saml_token,
                                  DIGEST: unicode_digest}
        return json.dumps(py_obj,
                          check_circular=False,
                          separators=(',', ':'),
                          cls=DecimalEncoder)


class JSONSSOVerifier(RequestProcessor):
    """
    This class is used to verify the authenticity of the request
    message by verifying the digest present in the security context
    block.
    """
    def process(self, input_message):
        """
        Verify the input JSON message.

        For verification, we need 4 things:

        1. algorithm: extracted from security context
        2. certificate: public key of the principal embedded in the
        SAML token is used
        3. digest: value field from signature block
        4. canonical msg: signature block is removed from the request
        and the remaining part is canonicalized

        Sample input security context:
        {
            'schemeId': 'SAML_TOKEN',
            'signatureAlgorithm': <ALGORITHM>,
            'signature': {
                'samlToken': <SAML_TOKEN>,
                'value': <DIGEST>
            }
            'timestamp': {
                'created': '2012-10-26T12:24:18.941Z',
                'expires': '2012-10-26T12:44:18.941Z',
            }
        }

        :type  input_message: :class:`str`
        :param input_message: Input JSON request message
        :rtype: :class:`str`
        :return: JSON request message after signature verification
        """
        if not input_message:
            return None

        if isinstance(input_message, six.binary_type):
            unicode_input_message = input_message.decode()
        else:
            unicode_input_message = input_message
        if SAML_SCHEME_ID not in unicode_input_message:
            return input_message

        py_obj = json.loads(unicode_input_message, parse_float=decimal.Decimal)
        json_params = py_obj.get(PARAMS)  # pylint: disable=E1103
        execution_ctx = json_params.get(EXECUTION_CONTEXT)
        sec_ctx = execution_ctx.get(SECURITY_CONTEXT)

        signature = sec_ctx.get(SIGNATURE)
        del sec_ctx[SIGNATURE]

        base64_encoded_digest = signature.get(DIGEST).encode()
        digest = b64decode(base64_encoded_digest)
        jws_algorithm = sec_ctx.get(SIGNATURE_ALGORITHM)
        algorithm = algorithm_map.get(jws_algorithm)
        saml_token = signature.get(SAML_TOKEN)
        certificate = _extract_certificate(saml_token)

        pubkey = crypto.load_certificate(
            crypto.FILETYPE_PEM, _prep_certificate(certificate))
        canonical_message = JSONCanonicalizer.canonicalize_py_obj(py_obj)
        crypto.verify(
            pubkey, digest, canonical_message.encode(), algorithm)

        sec_ctx[SAML_TOKEN] = saml_token
        sec_ctx[AUTHENTICATED] = True
        sec_ctx[SIGNATURE_ALGORITHM] = jws_algorithm

        return json.dumps(py_obj,
                          check_circular=False,
                          separators=(',', ':'),
                          cls=DecimalEncoder)


def _extract_element(xml, element_name, namespace):
    """
    An internal method provided to extract an element from the given XML.

    :type  xml: :class:`str`
    :param xml: The XML string from which the element will be extracted.
    :type  element_name: :class:`str`
    :param element_name: The element that needs to be extracted from the XML.
    :type  namespace: :class:`dict`
    :param namespace: A dict containing the namespace of the element to be
        extracted.
    :rtype: etree element.
    :return: The extracted element.
    """
    assert(len(namespace) == 1)
    result = xml.xpath("//%s:%s" % (list(namespace.keys())[0], element_name),
                       namespaces=namespace)
    if result and len(result) == 1:
        return result[0]
    else:
        raise KeyError("%s does not seem to be present or valid in the XML." %
                       element_name)


def _prep_private_key(private_key):
    """
    Append proper prefix and suffix text to a private key. There is no
    standard way for storing certificates. OpenSSL expects the demarcation
    text. This method makes sure that the text the markers are present.

    :type text: :class:`str`
    :param text: The private key of the service user.

    :rtype: :class:`str`
    :return: Normalized private key.
    """
    if not key_regex.search(private_key):
        return """-----BEGIN RSA PRIVATE KEY-----
%s
-----END RSA PRIVATE KEY-----""" % private_key
    return private_key


def _prep_certificate(certificate):
    """
    Append proper prefix and suffix text to a certificate. There is no
    standard way for storing certificates. OpenSSL expects the demarcation
    text. This method makes sure that the text the markers are present.

    :type text: :class:`str`
    :param text: The certificate of the service user.

    :rtype: :class:`str`
    :return: Normalized certificate
    """
    if not certificate.startswith('-----BEGIN CERTIFICATE-----'):
        return """-----BEGIN CERTIFICATE-----
%s
-----END CERTIFICATE-----""" % certificate
    return certificate


def _extract_certificate(hok_token):
    """
    Extract Certificate of the principal from Holder of Key SAML token

    :type  hok_token: :class:`str`
    :param hok_token: Holder of key SAML token
    :rtype: :class:`str`
    :return: Certificate of the principal
    """
    from lxml import etree
    xml = etree.fromstring(hok_token)
    subject = _extract_element(
        xml,
        'SubjectConfirmationData',
        {'saml2': 'urn:oasis:names:tc:SAML:2.0:assertion'})

    xml_certificate = subject.find('./' + CERT_NS + 'KeyInfo/'
                                   + CERT_NS + 'X509Data/'
                                   + CERT_NS + 'X509Certificate')
    xml_certificate = _get_element_text(xml_certificate)
    return xml_certificate.replace('\\n', '\n')


def _generate_request_timestamp():
    """
    Generate a timestamp for the request. This will be embedded in the security
    context of the request to protect it against replay attacks

    :rtype: :class:`dict`
    :return: Timestamp block that can be inserted in security context
    """
    created_dt = datetime.datetime.utcnow()
    offset = datetime.timedelta(minutes=REQUEST_VALIDITY)
    created = DateTimeConverter.convert_from_datetime(created_dt)
    expires = DateTimeConverter.convert_from_datetime(created_dt + offset)
    return {EXPIRES: expires, CREATED: created}


def _get_element_text(element):
    """
    Reading element.text is unsafe because of comments that may be embedded
    in certain important fields by an attacker.
    To ensure that we're getting the whole contents of the field this
    method concatenates all text children of the given element.

    Sample:
    <name>root<!-- -->less-user</name> --> "rootless-user"
    <name>alpha<x>bravo</x>charlie</name> --> "alpha"
    <name></name> --> None

    :type  element: :class:`str`
    :param element: XML document element
    :rtype: :class:`str`
    :return: XML document stripped off comment
    """
    from lxml import etree
    parts = []
    if element.text is not None:
        parts.append(element.text)
    for child in element.iterchildren():
        if child.tag is etree.Comment:
            if child.tail is not None:
                parts.append(child.tail)
        else:
            break
    if not parts:
        return None
    return "".join(parts)
