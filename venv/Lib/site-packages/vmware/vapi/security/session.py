"""
Session Security Helper
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.core import SecurityContext
from vmware.vapi.lib.constants import SCHEME_ID
from vmware.vapi.security.rest import SecurityContextParser

SESSION_SCHEME_ID = 'com.vmware.vapi.std.security.session_id'
SESSION_ID = 'sessionId'
# String used to identify session identifier in REST API HTTP headers
REST_SESSION_ID_KEY = 'vmware-api-session-id'
REQUIRE_HEADER_AUTHN = 'vmware-use-header-authn'


def create_session_security_context(session_id):
    """
    Create a security context for Session Id based authentication
    scheme

    :type  session_id: :class:`str`
    :param session_id: Session ID
    :rtype: :class:`vmware.vapi.core.SecurityContext`
    :return: Newly created security context
    """
    return SecurityContext({SCHEME_ID: SESSION_SCHEME_ID,
                            SESSION_ID: session_id})


class SessionSecurityContextParser(SecurityContextParser):
    """
    Security context parser used by the REST presentation layer
    that builds a security context if the REST request has session
    identifier either in the header or in the cookie.
    """
    def __init__(self):
        """
        Initialize SessionSecurityContextParser
        """
        SecurityContextParser.__init__(self)

    def build(self, request):
        """
        Build the security context if the request has the header
        that contains the session identifier or a cookie that has
        the session identifier.

        The method will first check for session identifier in the cookie,
        if it is not present, then it will check in the HTTP headers.
        The session security context is created based on the first session
        identifier it finds.

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`vmware.vapi.core.SecurityContext` or ``None``
        :return: Security context object
        """
        if request.cookies:
            session_id = request.cookies.get(REST_SESSION_ID_KEY)
            if session_id:
                return create_session_security_context(session_id)
        else:
            session_id = request.headers.get(REST_SESSION_ID_KEY)
            if session_id:
                return create_session_security_context(session_id)
