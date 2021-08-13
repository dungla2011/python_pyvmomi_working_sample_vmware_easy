"""
AuthenticationChain processor
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class AuthenticationChain(object):
    """
    Implementations of this interface are used to chain authentication when
    there is intermediary between the client and the server i.e. an
    aggregator node.
    """

    def next_context(self, ctx):
        """
        Returns the next security context based on the current context

        :type  ctx: :class:`vmware.vapi.core.SecurityContext`
        :param ctx: Current security context
        :rtype: :class:`vmware.vapi.core.SecurityContext`
        :return: Next security context
        """
        raise NotImplementedError
