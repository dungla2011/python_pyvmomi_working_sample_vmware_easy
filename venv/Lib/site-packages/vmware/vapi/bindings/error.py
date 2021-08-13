"""
Error classes and factory
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.bindings.struct import VapiStruct


class VapiError(VapiStruct, Exception):
    """
    Representation of VMODL Error in python language bindings
    """
    def __init__(self, error_value=None):
        """
        Initialize VapiError

        :type  error_value: :class:`vmware.vapi.data.value.ErrorValue` or
            :class:`None`
        :param error_value: ErrorValue to be used for VapiError
        """
        VapiStruct.__init__(self, struct_value=error_value)
        Exception.__init__(self)

    def get_error_value(self):
        """
        Returns the corresponding ErrorValue for the VapiError class

        :rtype: :class:`vmware.vapi.data.value.ErrorValue`
        :return: ErrorValue for this VapiError
        """
        return self.get_struct_value()


class UnresolvedError(VapiError):
    """
    VapiError which represents a VMODL2 error that was reported but couldn't
    be resolved
    """
    pass
