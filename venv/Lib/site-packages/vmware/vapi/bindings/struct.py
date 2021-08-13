"""
Bindings data classes
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2016 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import decimal
import json
import six
import sys

from vmware.vapi.bindings.common import raise_core_exception
from vmware.vapi.data.serializers import cleanjson
from vmware.vapi.data.value import StructValue
from vmware.vapi.lib.converter import Converter


# TODO: Split this into static and dynamic structures.
class VapiStruct(object):
    """
    Representation of IDL Structure in python language bindings
    """
    _validator_list = []
    # Dict of canonical to pep names for fields whose canonical name does not
    # match the pep name
    _canonical_to_pep_names = {}

    def __init__(self, struct_value=None, rest_converter_mode=None):
        """
        Initialize VapiStruct

        :type  mappings: :class:`dict` or :class:`None`
        :param mappings: A mapping for all field names whose canonical name does
                         not match PEP8 standard name
        :type  rest_converter_mode: :class:`str` or :class:`None`
        :param rest_converter_mode: Converter mode to be used to be be
            compatible for Vapi Rest. If None or unknown string value,
            then the default Json Rpc converter is used
        :type  struct_value: :class:`vmware.vapi.data.value.StructValue`
        :param struct_value: StructValue to be used for VapiStruct
            or :class:`None`
        """
        # fields will either be in native form or in unknown
        # fields
        self._extra_fields = None
        if (struct_value is not None and
                not isinstance(struct_value, StructValue)):
            raise TypeError(
                'struct_value must be of type '
                + '\'vmware.vapi.data.value.StructValue\' or None')
        self._struct_value = struct_value
        self._rest_converter_mode = rest_converter_mode

    def get_field(self, attr):
        """
        Returns the struct field value

        :type  attr: :class:`str`
        :param attr: Canonical field name
        :rtype: :class:`object`
        :return: Field value
        """
        if (self._canonical_to_pep_names and
                attr in self._canonical_to_pep_names):
            return getattr(self, self._canonical_to_pep_names[attr])
        else:
            return getattr(self, attr)

    @classmethod
    def validate_struct_value(cls, struct_value):
        """
        Validate if the given struct value satisfies all
        the constraints of this VapiStruct.

        :type  struct_value: :class:`vmware.vapi.data.value.StructValue`
        :param struct_value: StructValue to be validated
        :type  validators: :class:`list` of
            :class:`vmware.vapi.data.validator.Validator`
        :param validators: List of validators
        :raise :class:`vmware.vapi.exception.CoreException` if a constraint is
            not satisfied
        """
        if cls._validator_list:
            for validator in cls._validator_list:
                msg_list = validator.validate(struct_value, None)
                raise_core_exception(msg_list)

    def validate_constraints(self):
        """
        Validate if the current VapiStruct instance satisfies all the
        constraints of this VapiStruct type.

        :raise :class:`vmware.vapi.exception.CoreException` if a constraint is
            not satisfied
        """
        struct_value = self.get_struct_value()
        self.validate_struct_value(struct_value)

    @classmethod
    def get_binding_type(cls):
        """
        Returns the corresponding BindingType for the VapiStruct class

        :rtype: :class:`vmware.vapi.bindings.type.BindingType`
        :return: BindingType for this VapiStruct
        """
        return getattr(cls, '_binding_type', None)

    @classmethod
    def _set_binding_type(cls, binding_type):
        """
        Set the underlying BindingType for this VapiStruct.

        :type  binding_type: :class:`vmware.vapi.bindings.type.BindingType`
        :param binding_type: BindingType for this VapiStruct
        """
        cls._binding_type = binding_type

    def get_struct_value(self):
        """
        Returns the corresponding StructValue for the VapiStruct class

        :rtype: :class:`vmware.vapi.data.value.StructValue`
        :return: StructValue for this VapiStruct
        """
        # For dynamic structures
        if self._struct_value:
            return self._struct_value
        else:
            # For static structures import TypeConverter here since
            # otherwise it causes circular imports
            from vmware.vapi.bindings.converter import TypeConverter
            struct_value = TypeConverter.convert_to_vapi(
                py_val=self, binding_type=self._binding_type)
            return struct_value

    def _get_extra_fields(self):
        """
        Get the fields that are not part of the static definition for this
        VapiStruct. This is an internal method and should only be used by vAPI
        runtime.

        :rtype  :class:`dict` of :class:`str` and
            :class:`vmware.vapi.data.value.DataValue`
        :return Fields not part of the static definition for this VapiStruct
        """
        return self._extra_fields or {}

    def _set_extra_fields(self, extra_fields=None):
        """
        Set the fields that are not part of the static definition for this
        VapiStruct. This is an internal method and should only be used by vAPI
        runtime.

        :type  extra_fields: :class:`dict` of :class:`str` and
            :class:`vmware.vapi.data.value.DataValue` or :class:`None`
        :param extra_fields: Fields not part of the static definition for
            this VapiStruct
        """
        self._extra_fields = extra_fields

    @classmethod
    def _get_pep_name(cls, canonical_name):
        """
        Return the pep name for the provided canonical name

        :rtype: :class:`str`
        :return: Pep name used in the binding
        """
        if (cls._canonical_to_pep_names
                and canonical_name in cls._canonical_to_pep_names):
            return cls._canonical_to_pep_names[canonical_name]
        else:
            return Converter.canonical_to_pep(canonical_name)

    def convert_to(self, cls):
        """
        Convert the underlying StructValue to an instance of the provided class
        if possible.  Conversion will be possible if the StructValue contains
        all the fields expected by the provided class and the type of the value
        in each fields matches the type of the field expected by the provided
        class.

        :type  cls: :class:`vmware.vapi.data.value.StructValue`
        :param cls: The type to convert to
        :rtype: :class:'vmware.vapi.bindings.struct.VapiStruct'
        :return: The converted value
        """
        # Import TypeConverter here since otherwise it causes circular imports
        from vmware.vapi.bindings.converter import TypeConverter
        return TypeConverter.convert_to_python(
            vapi_val=self.get_struct_value(),
            binding_type=cls.get_binding_type(),
            rest_converter_mode=self._rest_converter_mode)

    def to_json(self):
        """
        Convert the object into a json string.

        :rtype: :class:`str`
        :return: JSON string representation of this object
        """
        struct_value = self.get_struct_value()
        return cleanjson.DataValueConverter.convert_to_json(struct_value)

    def to_dict(self):
        """
        Convert the object into a python dictionary. Even the nested types
        are converted to dictionaries.

        :rtype: :class:`dict`
        :return: Dictionary representation of this object
        """
        # TODO: Implement native converter from DataValue -> Dictionary
        # to improve performance if it is used heavily
        return json.loads(self.to_json(), parse_float=decimal.Decimal)

    def _get_attrs(self):
        """
        Returns the attributes of the vAPI structure object

        :rtype: :class:`list` of :class:`str`
        :return: List of attributes of this object
        """
        # Using getmembers in inspect to return all the attributes
        # of this object. And later filter those to get only the
        # public data attributes
        return [k for k in six.iterkeys(vars(self))
                if not k.startswith('_')]

    def __eq__(self, other):
        if other is None:
            return False
        for attr in self._get_attrs():
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        class_name = self.__class__.__name__
        attrs = self._get_attrs()
        result = ', '.join(
            ['%s=%s' % (attr, repr(getattr(self, attr)))
             for attr in attrs])
        return '%s(%s)' % (class_name, result)

    def __str__(self):
        attrs = self._get_attrs()
        result = ', '.join(
            ['%s : %s' % (attr, str(getattr(self, attr)))
             for attr in attrs])
        return '{%s}' % result

    def __hash__(self):
        return str(self).__hash__()


class PrettyPrinter(object):
    """
    Helper class to pretty print Python native values (with special support
    for VapiStruct objects).
    """
    def __init__(self, stream=sys.stdout, indent=2):
        """
        Initialize PrettyPrinter

        :type  stream: :class:`object`
        :param stream: A stream object that implements File protocol's
            write operation
        :type  indent: :class:`int`
        :param indent: Indentation to be used for new lines
        """
        self._stream = stream
        self._indent = indent

    def pprint(self, value, level=0):
        """
        Print a Python native value

        :type  value: :class:`vmware.vapi.bindings.struct.VapiStruct`
        :param value: VapiStruct to be pretty printed
        :type  level: :class:`int`
        :param level: Indentation level
        """
        self._process_value(value, level)

    def _print_level(self, value, level, newline=True):
        """
        Print data at a given identation level

        :type  value: :class:`str`
        :param value: String to be printed
        :type  level: :class:`int`
        :param level: Indentation level
        :type  newline: :class:`bool`
        :param newline: If true, prints a new line after the data. If false,
            only prints the data
        """
        if level:
            self._stream.write('  ' * level + value)
        else:
            self._stream.write(value)
        if newline:
            self._stream.write('\n')

    def _process_value(self, value, level=0):
        """
        Process a value

        :type  value: :class:`object`
        :param value: Value to be processed
        :type  level: :class:`int`
        :param level: Indentation level
        """
        if isinstance(value, VapiStruct):
            self._pprint_struct(value, level + self._indent)
        elif isinstance(value, dict):
            self._pprint_dict(value, level + self._indent)
        elif isinstance(value, list):
            self._pprint_list(value, level + self._indent)
        elif isinstance(value, six.string_types):
            self._print_level("'%s'," % value, 0)
        elif isinstance(value, six.integer_types):
            self._print_level('%s,' % value, 0)
        elif value is None:
            self._print_level('None,', 0)
        else:
            self._print_level('%s,' % value, level)

    def _pprint_struct(self, value, level=0):
        """
        Pretty print a struct

        :type  value: :class:`vmware.vapi.bindings.struct.VapiStruct`
        :param value: Value to be processed
        :type  level: :class:`int`
        :param level: Indentation level
        """
        class_name = value.__class__.__name__
        self._print_level(class_name + '(', 0)
        for k in sorted(value._get_attrs()):  # pylint: disable=W0212
            v = getattr(value, k)
            self._print_level('%s=' % k, level, False)
            self._process_value(v, level)
        self._print_level('),', level - self._indent)

    def _pprint_dict(self, value, level=0):
        """
        Pretty print a dictionary

        :type  value: :class:`dict`
        :param value: Value to be processed
        :type  level: :class:`int`
        :param level: Indentation level
        """
        if not value:
            self._print_level('{},', 0)
            return
        self._print_level('{', 0)
        for k in sorted(value.keys()):
            self._print_level("'%s':" % k, level, False)
            self._process_value(value[k], level)
        self._print_level('},', level - self._indent)

    def _pprint_list(self, value, level=0):
        """
        Pretty print a list

        :type  value: :class:`list`
        :param value: Value to be processed
        :type  level: :class:`int`
        :param level: Indentation level
        """
        if not value:
            self._print_level('[],', 0)
            return
        self._print_level('[', 0)
        for v in value:
            self._print_level('', level, False)
            self._process_value(v, level)
        self._print_level('],', level - self._indent)
