"""
Authorization Handler interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class AuthorizationHandler(object):
    """
    The AuthorizationHandler interface is used to verify the authentication
    data provided in the security context against an identity source.
    """

    def authorize(self, service_id, operation_id, ctx):
        """
        Verifies the provided authentication data against the relevant identity
        source.

        :type  ctx: :class:`vmware.vapi.core.SecurityContext`
        :param ctx: Security context for the method

        :rtype: :class:`bool`
        :return: True if authorization was successful
        """
        raise NotImplementedError

    def __hash__(self):
        return str(self).__hash__()
