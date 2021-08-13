"""
CSP Refresh token based SecurityContextFilter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.security.client.security_context_filter import (
    SecurityContextFilter)
from vmware.vapi.security.oauth import create_oauth_security_context


class CSPSecurityContextFilter(SecurityContextFilter):
    """
    CSP Security Context filter in API Provider chain adds the security
    context based on a refresh token to the execution context passed in.
    """

    def __init__(self, session, refresh_token, refresh_url):
        """
        Initialize SecurityContextFilter

        :type  session: :class:`requests.Session`
        :param session: Requests Session object to use for making HTTP calls
        :type  refresh_token: :class:`str`
        :param refresh_token: Refresh token to use for obtaining an access token
        :type  refresh_url: :class:`str`
        :param refresh_url: URL that allows exchanging a refresh token for an
            access token
        """
        SecurityContextFilter.__init__(self, None)
        self._session = session
        self._refresh_token = refresh_token
        self._data = {'refresh_token': refresh_token}
        self._refresh_url = refresh_url
        self._access_token = None

    def get_max_retries(self):
        """
        Get the max number of retries

        :rtype: :class:`int`
        :return: Number of retries
        """
        return 1

    def get_security_context(self, on_error):
        """
        Retrieve security context. If this method is called after an error
        occured, then a new access token is obtained using the refresh token and
        a new security context is created.

        :type  on_error: :class:`bool`
        :param on_error: Whether this method is called after getting an error
        :rtype: :class:`vmware.vapi.core.SecurityContext`
        :return: Security context
        """
        if on_error or not self._access_token:
            token = self._session.post(self._refresh_url, data=self._data).json()
            self._access_token = token['access_token']
        return create_oauth_security_context(self._access_token)

    def should_retry(self, error_value):
        """
        Returns whether the request should be retried or not based on the error
        specified.

        :type  error_value: :class:`vmware.vapi.data.value.ErrorValue`
        :param error_value: Method error
        :rtype: :class:`bool`
        :return: Returns True if request should be retried in case the error is
            either Unauthenticated or Unauthorized else False
        """
        if error_value and error_value.name in [
                'com.vmware.vapi.std.errors.unauthenticated',
                'com.vmware.vapi.std.errors.unauthorized']:
            return True
        return False
