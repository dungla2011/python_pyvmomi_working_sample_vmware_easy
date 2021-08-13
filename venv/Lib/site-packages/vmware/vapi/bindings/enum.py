"""
Bindings data classes
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2016 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six


class Enum(six.text_type):
    """
    Representation of IDL Enum in python language bindings
    """
    _binding_type = None
    _values = []

    @classmethod
    def _set_binding_type(cls, binding_type):
        """
        Set the underlying BindingType for this VapiStruct.

        :type  binding_type: :class:`vmware.vapi.data.value.BindingType`
        :param binding_type: BindingType for this VapiStruct
        """
        cls._binding_type = binding_type

    @classmethod
    def get_binding_type(cls):
        """
        Returns the corresponding BindingType for the VapiStruct class

        :rtype: :class:`vmware.vapi.data.value.BindingType` or ``None``
        :return: BindingType for this VapiStruct
        """
        return cls._binding_type

    @classmethod
    def get_values(cls):
        """
        Returns the list of all the possible enum values

        :rtype: :class:`list` of :class:`vmware.vapi.bindings.enum.Enum`
        :return: List of all possible enum values
        """
        return cls._values

    @classmethod
    def _set_values(cls, values):
        """
        Set the list of the enum values and assign them to respective class
        attributes

        :type :class:`list` of :class:`vmware.vapi.bindings.enum.Enum`
        :param List of all possible enum values
        """
        cls._values = list(values)
        for val in cls._values:
            setattr(cls, val, val)

    def is_unknown(self):
        """
        Returns whether the enum value stored is one of the known values or not

        :rtype: :class:`bool`
        :return: True if the enum value is not known
        """
        return not (self in self._values)

    def __repr__(self):
        class_name = self.__class__.__name__
        return '%s(string=%s)' % (class_name, six.text_type.__repr__(self))
