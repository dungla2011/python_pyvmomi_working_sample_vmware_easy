# -*- coding: utf-8 -*-
"""
User password Security Helper
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from base64 import b64decode

from vmware.vapi.core import SecurityContext
from vmware.vapi.lib.constants import SCHEME_ID
from vmware.vapi.security.rest import SecurityContextParser

USER_PASSWORD_SCHEME_ID = 'com.vmware.vapi.std.security.user_pass'
USER_KEY = 'userName'
PASSWORD_KEY = 'password'
HTTP_AUTH_HEADER_NAME = 'Authorization'
HTTP_BASIC_AUTH_HEADER_PARAM = 'Basic'


def create_user_password_security_context(user_name, password):
    """
    Create a security context for Username-Password based authentication
    scheme

    :type  user_name: :class:`str`
    :param user_name: Name of the user
    :type  password: :class:`str`
    :param password: Password of the user
    :rtype: :class:`vmware.vapi.core.SecurityContext`
    :return: Newly created security context
    """
    return SecurityContext({SCHEME_ID: USER_PASSWORD_SCHEME_ID,
                            USER_KEY: user_name,
                            PASSWORD_KEY: password})


class UserPasswordSecurityContextParser(SecurityContextParser):
    """
    Security context parser used by the REST presentation layer
    that builds a security context if the REST request has
    username/password credentials in the HTTP header.
    """
    def __init__(self):
        """
        Initialize UserPasswordSecurityContextParser
        """
        SecurityContextParser.__init__(self)

    def build(self, request):
        """
        Build the security context if the request has authorization
        header that contains base64 encoded string of username/password.

        If the request authorization header doesn't have the username/password,
        this method returns None.

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`vmware.vapi.core.SecurityContext` or ``None``
        :return: Security context object
        """
        username, password = self._get_username_password_from_auth_header(
            request)
        if username is not None and password is not None:
            return create_user_password_security_context(username, password)
        return None

    def _get_username_password_from_auth_header(self, request):
        """
        Werkzeug uses "latin-1" to encode/decode. We need to use "utf-8". Hence,
        manually parse the Authorization header and extract the username and
        password.

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple of username and password
        """
        username, password = None, None
        if HTTP_AUTH_HEADER_NAME in request.headers:
            http_auth_header_value = request.headers[HTTP_AUTH_HEADER_NAME]
            if HTTP_BASIC_AUTH_HEADER_PARAM in http_auth_header_value:
                http_auth_header_tokens = http_auth_header_value.split(' ')
                if len(http_auth_header_tokens) > 1:
                    user_password_str = b64decode(
                        http_auth_header_tokens[1]).decode('utf-8')
                    if ':' in user_password_str:
                        username, password = user_password_str.split(':', 1)
        return username, password
