"""
Oauth2 Security Helper
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.core import SecurityContext
from vmware.vapi.lib.constants import SCHEME_ID
from vmware.vapi.security.rest import SecurityContextParser

OAUTH_SCHEME_ID = 'com.vmware.vapi.std.security.oauth'
ACCESS_TOKEN = 'accessToken'
AUTHORIZATION = 'Authorization'
BEARER = 'bearer'


def create_oauth_security_context(access_token):
    """
    Create a security context for Oauth2 based authentication
    scheme

    :type  access_token: :class:`str`
    :param access_token: Access token
    :rtype: :class:`vmware.vapi.core.SecurityContext`
    :return: Newly created security context
    """
    return SecurityContext({SCHEME_ID: OAUTH_SCHEME_ID,
                            ACCESS_TOKEN: access_token})


class OAuthSecurityContextParser(SecurityContextParser):
    """
    Security context parser used by the REST presentation layer
    that builds a security context if the REST request has OAuth2
    access token in the header.
    """
    def __init__(self):
        """
        Initialize OAuthSecurityContextParser
        """
        SecurityContextParser.__init__(self)

    def build(self, request):
        """
        Build the security context if the request has authorization
        header that contains OAuth2 access token.

        If the request authorization header doesn't have the OAuth2
        access token, this method returns None.

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`vmware.vapi.core.SecurityContext` or ``None``
        :return: Security context object
        """
        authorization = request.headers.get(AUTHORIZATION)
        if authorization:
            try:
                auth_type, auth_info = authorization.split(None, 1)
                if auth_type.lower() == BEARER:
                    return create_oauth_security_context(auth_info)
            except ValueError:
                return None
