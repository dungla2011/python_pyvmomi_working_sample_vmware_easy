"""
Security context parser interface for REST presentation layer
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class SecurityContextParser(object):
    """
    Base class for all security context builders
    """
    def build(self, request):
        """
        Build the security context based on the authentication
        information in the request.

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`vmware.vapi.core.SecurityContext`
        :return: Security context object
        """
        pass
