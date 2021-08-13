"""
Authentication Handler interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class AuthenticationHandler(object):
    """
    The AuthenticationHandler interface is used to verify the authentication
    data provided in the security context against an identity source.
    """

    def authenticate(self, ctx):
        """
        Verifies the provided authentication data against the relevant identity
        source.

        :type  ctx: :class:`vmware.vapi.core.SecurityContext`
        :param ctx: Security context for the method

        :rtype: :class:`vmware.vapi.security.user_identity.UserIdentity`
        :return: Authentication Identity for successful authentication,
                 False for failed authentication and None for invalid handler.
        """
        raise NotImplementedError

    def get_supported_scheme(self):
        """
        Get the scheme supported by this handler
        """
        raise NotImplementedError

    def __hash__(self):
        return str(self).__hash__()
