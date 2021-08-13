"""
Utility library for Provider modules
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.core import MethodResult, MethodDefinition
from vmware.vapi.data.value import StructValue, ListValue
from vmware.vapi.lib.constants import Introspection


def augment_method_result_with_errors(service_id, operation_id, method_result,
                                      errors_to_augment):
    """
    Returns a new method result that is identical to `method_result` except that
    the `errors_definition` field in the `output` (which is of type
    Operation.Info from Introspection service) contains the errors from the Info
    structure in `method_result` plus the errors in `errors_to_augment`. This
    code will be executed only for "get" operation in vAPI Operation
    Introspection service.

    :type  service_id: :class:`str`
    :param service_id: Service identifier
    :type  operation_id: :class:`str`
    :param operation_id: Operation identifier
    :type  method_result: :class:`vmware.vapi.core.MethodResult`
    :param method_result: Operation result
    :type  errors_to_augment: :class:`list` of
        :class:`vmware.vapi.data.value.StructValue`
    :param errors_to_augment: Errors to augment. These are struct values of type
        com.vmware.vapi.std.introspection.Operation.DataDefinition whose `type`
        field has the value ERROR
        to the DataDefinition type in Introspection service IDL.
    :rtype: :class:`vmware.vapi.data.value.DataValue`
    :return: Output data value
    """
    if method_result.success():
        if (service_id == Introspection.OPERATION_SVC and
                operation_id == 'get'):
            output = method_result.output
            augmented_output = StructValue(
                'com.vmware.vapi.std.introspection.operation.info')
            augmented_output.set_field(
                'input_definition',
                output.get_field('input_definition'))
            augmented_output.set_field(
                'output_definition',
                output.get_field('output_definition'))
            errors = ListValue()
            error_names = []
            for error_def in output.get_field('error_definitions'):
                errors.add(error_def)
                error_names.append(error_def.get_field('name').value.value)
            for error_def in errors_to_augment:
                if error_def.get_field('name').value.value not in error_names:
                    errors.add(error_def)
            augmented_output.set_field('error_definitions', errors)
            return MethodResult(output=augmented_output)
    return method_result


def augment_method_def_with_errors(method_def, errors):
    """
    Add errors reported by this ApiProviderFilter to a method definition.
    This method clones the input method definition and appends errors. It
    does not modify the parameter.

    :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
    :param method_def: Method definition
    :type  errors: :class:`list` of
        :class:`vmware.vapi.data.definition.ErrorDefinition`
    :param errors: Error definitions to augment to MethodDefinition
    :rtype: :class:`vmware.vapi.core.MethodDefinition`
    :return: Method definition after augmenting the errors
    """
    method_errors = method_def.get_error_definitions()
    return MethodDefinition(method_def.get_identifier(),
                            method_def.get_input_definition(),
                            method_def.get_output_definition(),
                            method_errors.union(errors))
