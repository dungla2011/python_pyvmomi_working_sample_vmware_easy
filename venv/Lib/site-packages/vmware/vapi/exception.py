#!/usr/bin/env python

"""
vAPI CoreException Class
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


# The plan is to rename this to VapiException once the original VapiException
# (above) is eliminated.
class CoreException(Exception):
    """
    This exception is raised by various components of the vAPI runtime
    infrastructure to indicate failures in that infrastructure.

    Server-side the exception is caught by specific components and an
    internal_server_error is reported to the client that invoked the
    request.  Client-side the exception may be raised for certain failures
    before a request was sent to the server or after the response was
    received from the server.  Similarly, server-side the exception may
    be raised for failures that occur when a provider implementation
    invokes the vAPI runtime.

    This exception is not part of the vAPI message protocol, and it must
    never be raised by provider implementations.

    :type messages: generator of :class:`vmware.vapi.message.Message`
    :ivar messages: Generator of error messages describing why the Exception
                    was raised
    """

    def __init__(self, message, cause=None):
        """
        Initialize CoreException

        :type  message: :class:`vmware.vapi.message.Message`
        :param message: Description regarding why the Exception was raised
        :type  cause: :class:`Exception`
        :type  cause: Exception that led to this Exception
        """
        Exception.__init__(self, str(message))
        self._message = message
        self._cause = cause

    @property
    def messages(self):
        """
        :rtype: generator of :class:`vmware.vapi.message.Message`
        :return: Generator of error messages describing why the Exception
                 was raised
        """
        e = self
        while e:
            try:
                yield e._message  # pylint: disable=W0212
                e = e._cause      # pylint: disable=W0212
            except AttributeError:
                e = None

    # This method is primarily for use in tests
    def __eq__(self, other):
        return (isinstance(other, CoreException) and
                (list(self.messages) == list(other.messages)))

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        result = Exception.__str__(self)
        if self._cause is not None:
            cause_class = self._cause.__class__
            cause_class_name = '%s.%s' % (cause_class.__module__,
                                          cause_class.__name__)
            result = '%s, \n\tCaused by: %s: %s' % (result,
                                                    cause_class_name,
                                                    str(self._cause))
        return result

    def __hash__(self):
        return str(self).__hash__()
