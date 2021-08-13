"""
Skeleton helper classes
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import sys
import six
import threading

from vmware.vapi.bindings.error import VapiError
from vmware.vapi.bindings.converter import TypeConverter
from vmware.vapi.bindings.common import NameToTypeResolver
from vmware.vapi.bindings.task_helper import (
    is_task_operation, get_non_task_operation_name)
from vmware.vapi.bindings.type import (
    ListType, OptionalType, ReferenceType,
    StructType, DynamicStructType)
from vmware.vapi.core import ApiInterface, MethodIdentifier
from vmware.vapi.core import InterfaceDefinition, MethodResult, MethodDefinition
from vmware.vapi.core import InterfaceIdentifier
from vmware.vapi.data.value import OptionalValue
from vmware.vapi.exception import CoreException
from vmware.vapi.common.context import (
    clear_context, get_context, set_context, set_event)
from vmware.vapi.lib.constants import TaskType
from vmware.vapi.lib.context import insert_task_id
from vmware.vapi.lib.converter import Converter
from vmware.vapi.lib.log import get_vapi_logger, VapiFilter
from vmware.vapi.lib.std import make_error_value_from_msgs, make_std_error_def
from vmware.vapi.l10n.runtime import message_factory

# Add VapiFilter symbol to this module for backwards compatibility
module = sys.modules[__name__]
setattr(module, VapiFilter.__name__, VapiFilter)

logger = get_vapi_logger(__name__)


class ApiInterfaceSkeleton(ApiInterface):
    """
    Skeleton class for :class:`ApiInterface`. This class implements the
    :class:`ApiInterface` interface.
    """

    # XXX These error definitions should be eliminated when we figure out
    #     where/how to get the error definitions used by the local provider
    _internal_server_error_def = make_std_error_def(
        'com.vmware.vapi.std.errors.internal_server_error')
    _invalid_argument_def = make_std_error_def(
        'com.vmware.vapi.std.errors.invalid_argument')
    _operation_not_found_def = make_std_error_def(
        'com.vmware.vapi.std.errors.operation_not_found')
    _unexpected_input_def = make_std_error_def(
        'com.vmware.vapi.std.errors.unexpected_input')

    # Errors that are reported by this class
    _error_defs_to_augment = (
        _internal_server_error_def,
        _invalid_argument_def,
        _unexpected_input_def
    )

    # Errors that are allowed be reported by provider implementations even
    # though they are not included in the VMODL2 throws clause.
    #
    # XXX: This should be removed when once the runtime/bindings
    # check for invocations using API features that are disabled by feature
    # switch and report these errors (so provider implementations don't need
    # to report them).
    _unchecked_error_defs = (
        _operation_not_found_def,
        _unexpected_input_def
    )

    def __init__(self, iface_name, impl, operations, error_types):
        """
        Initialize the ApiInterface skeleton class

        :type  iface_name: :class:`str`
        :param iface_name: Interface name
        :type  impl: :class:`VapiInterface`
        :param impl: Class that implements this interface
        :type  operations: :class:`dict`
        :param operations: Description of the operations in this service
        :type  error_types: :class:`list` of
            :class:`vmware.vapi.bindings.type.ErrorType`
        :param error_types: error types to be registered in this configuration
        """
        self._operations = operations
        self._iface_id = InterfaceIdentifier(iface_name)
        operation_ids = [MethodIdentifier(self._iface_id, operation_name)
                         for operation_name in six.iterkeys(self._operations)]
        self._iface_def = InterfaceDefinition(self._iface_id,
                                              operation_ids)
        self._impl = impl
        error_types = error_types or []
        self._resolver = NameToTypeResolver(
            {e.definition.name: e for e in error_types})
        ApiInterface.__init__(self)

    @staticmethod
    def _pepify_args(meth_args):
        """
        Converts all the keys of given keyword arguments into PEP8 standard
        names

        :type  meth_args: :class:`dict`
        :param meth_args: The keyword arguments to be converted
        :rtype:  :class:`dict`
        :return: The converted keyword arguments
        """
        new_args = {}
        for k, v in six.iteritems(meth_args):
            new_args[Converter.canonical_to_pep(k)] = v
        return new_args

    @classmethod
    def is_set_optional_field(cls, value):
        """
        Returns true if the value is OptionalValue and it is set

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: value to be checked
        :rtype: :class:`bool`
        :return: True if the value is OptionalValue and is set, False otherwise
        """
        return not isinstance(value, OptionalValue) or value.is_set()

    @classmethod
    def check_for_unknown_fields(cls, value_type, value):
        """
        Check if the StructValues inside the input DataValue has any
        unknown fields

        :type  value_type: :class:`vmware.vapi.bindings.type.BindingType`
        :param value_type: Binding Type
        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: DataValue
        :rtype: :class:`vmware.vapi.data.value.ErrorValue` or ``None``
        :return: ErrorValue describing the unknown fields or None if no
                 unknown fields were found
        """
        if isinstance(value_type, ReferenceType):
            value_type = value_type.resolved_type

        if isinstance(value_type, DynamicStructType):
            pass
        elif isinstance(value_type, StructType):
            expected_field_names = value_type.get_field_names()
            unexpected_fields = set([  # pylint: disable=consider-using-set-comprehension
                field for field in value.get_field_names()
                if field not in expected_field_names
                and cls.is_set_optional_field(value.get_field(field))
            ])
            if unexpected_fields:
                msg = message_factory.get_message(
                    'vapi.data.structure.field.unexpected',
                    repr(unexpected_fields), value.name)
                logger.debug(msg)
                return make_error_value_from_msgs(cls._unexpected_input_def,
                                                  msg)
            for field in expected_field_names:
                field_value = value.get_field(field)
                field_type = value_type.get_field(field)
                error = ApiInterfaceSkeleton.check_for_unknown_fields(
                    field_type, field_value)
                if error:
                    return error
        elif isinstance(value_type, ListType):
            element_type = value_type.element_type
            if isinstance(element_type, (
                    ListType, OptionalType, StructType, ReferenceType)):
                for element in value:
                    error = ApiInterfaceSkeleton.check_for_unknown_fields(
                        element_type, element)
                    if error:
                        return error
        elif isinstance(value_type, OptionalType):
            if value.is_set():
                return ApiInterfaceSkeleton.check_for_unknown_fields(
                    value_type.element_type, value.value)
        return None

    def get_identifier(self):
        return self._iface_id

    def get_definition(self):
        return self._iface_def

    def get_method_definition(self, method_id):
        op_info = self._operations.get(method_id.get_name())
        if op_info is None:
            return None

        errors_defs = [e.definition for e in op_info['errors']]
        for error_def in self._error_defs_to_augment:
            if error_def not in errors_defs:
                errors_defs.append(error_def)

        # XXX: This loop should be removed when once the runtime/bindings
        # check for invocations using API features that are disabled by feature
        # switch and report these errors (so provider implementations don't need
        # to report them).
        for error_def in self._unchecked_error_defs:
            if error_def not in errors_defs:
                errors_defs.append(error_def)

        return MethodDefinition(method_id,
                                op_info['input_type'].definition,
                                op_info['output_type'].definition,
                                errors_defs)

    def _invoke_task_operation(self, ctx, method_id, method, method_args):
        """
        Invokes the task operations by adding them in thread pool queue.

        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :type  method_id: :class:`str`
        :param method_id: Method id
        :type  method: :class:`str`
        :param method: Method name
        :type  method_args: :class:`args`
        :param method_args: Method input parameters

        :rtype: :class:`tuple` of :class:`str` or
                :class:`vmware.vapi.core.MethodResult` and :class:`bool`
        :return: Tuple of task id and boolean value or Method Result
        """

        from vmware.vapi.lib.thread_pool import get_threadpool
        from vmware.vapi.task.task_manager_impl import get_task_manager
        task_manager = get_task_manager()
        thread_pool = get_threadpool()
        service_id = method_id.get_interface_identifier().get_name()
        operation_id = method_id.get_name()
        op_info = self._operations.get(operation_id)
        task_id = task_manager.create_task(
                                None,
                                service_id,
                                operation_id,
                                False,
                                op_info['errors'])
        insert_task_id(ctx.application_context, task_id)
        event = threading.Event()
        accept_timeout = 30
        if is_task_operation(method_id.get_name()):
            work_item = thread_pool.queue_work(
                                        self._invoke_method,
                                        ctx, method,
                                        method_args, event)
            event_set = event.wait(accept_timeout)

            # In case of provider throwing an error before  accepting task
            # remove task from task manager.
            if work_item.err:
                task_manager.remove_task(task_id)
                return work_item.err, None

            # In case of provider not accepting task remove task from task
            # manager.
            if not event_set:
                task_manager.remove_task(task_id)
                return None, False

            return task_id, event_set
        else:
            # If $task is not present in method id for a task operation
            # even then we will still use a separate thread in threadpool
            # and wait for its completion to return the result that's
            # to ensure provider implementation can be same irrespective
            # of client calling for task or non-task version of operation
            result = thread_pool.queue_work_and_wait(self._invoke_method,
                                                     ctx,
                                                     method,
                                                     method_args,
                                                     event)

            return result[1], None

    def _invoke_method(self, ctx, method, method_args, event):
        """
        Invoke the provider method after setting appropriate context and event

        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :type  method: :class:`str`
        :param method: Method name
        :type  method_args: :class:`args`
        :param method_args: Method input parameters
        :type  event: :class:`threading.Event`
        :param event: Event object

        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result of the method invocation
        """
        logger.debug('Setting execution ctx for the new thread')
        set_context(ctx)
        set_event(event)
        result = method(**method_args)
        clear_context()
        return result

    def invoke(self, ctx, method_id, input_value):
        """
        Invokes the specified method using the execution context and
        the input provided

        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters

        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result of the method invocation
        """
        op_info = self._operations.get(method_id.get_name())

        # Set execution context
        set_context(ctx)

        try:
            # input validators
            validators = op_info['input_value_validator_list']
            input_type = op_info['input_type']
            for validator in validators:
                msg_list = validator.validate(input_value, input_type)
                if msg_list:
                    error_value = make_error_value_from_msgs(
                        self._invalid_argument_def, *msg_list)
                    return MethodResult(error=error_value)
            error_value = ApiInterfaceSkeleton.check_for_unknown_fields(
                input_type, input_value)
            if error_value:
                return MethodResult(error=error_value)

            try:
                meth_args = TypeConverter.convert_to_python(
                    input_value, binding_type=input_type,
                    resolver=self._resolver)
            except CoreException as e:
                error_value = make_error_value_from_msgs(
                    self._invalid_argument_def, *e.messages)
                return MethodResult(error=error_value)

            method_name = Converter.canonical_to_pep(
                            get_non_task_operation_name(method_id.get_name()))
            method = getattr(self._impl, method_name)

            # If it's a task method then create a new thread to run provider
            # impl and return task id or result depending upon type of
            # invocation.
            if op_info['task_type'] != TaskType.NONE:
                meth_output, task_accepted = self._invoke_task_operation(
                    ctx, method_id, method, meth_args)

                if isinstance(meth_output, VapiError):
                    raise meth_output  # pylint: disable=raising-bad-type

                # In case of provider not accepting task throw an error.
                if task_accepted is False:
                    msg_list = [message_factory.get_message(
                                'vapi.bindings.skeleton.task.invalidstate')]
                    error_value = make_error_value_from_msgs(
                        self._internal_server_error_def,
                        *msg_list)
                    return MethodResult(error=error_value)
            else:
                meth_output = method(**meth_args)

            output_type = op_info['output_type']
            # output validators
            validators = op_info['output_validator_list']

            output = TypeConverter.convert_to_vapi(meth_output,
                                                   output_type)

            for validator in validators:
                msg_list = validator.validate(output, output_type)
                if msg_list:
                    error_value = make_error_value_from_msgs(
                        self._internal_server_error_def, *msg_list)
                    return MethodResult(error=error_value)
            result = MethodResult(output=output)
        except CoreException as e:
            logger.exception("Error in invoking %s - %s",
                             str(method_id), e)
            error_value = make_error_value_from_msgs(
                self._internal_server_error_def,
                *e.messages)
            result = MethodResult(error=error_value)
        except VapiError as e:
            exc_info = sys.exc_info()
            error_type = e.__class__.get_binding_type()
            try:
                error = TypeConverter.convert_to_vapi(e, error_type)
            except CoreException as ce:
                logger.error('Failed to convert %s to error type %s because %s',
                             e, error_type.name,
                             ' because '.join((e.def_msg for e in ce.messages)),
                             exc_info=exc_info)
                raise
            result = MethodResult(error=error)
        finally:
            # Reset the execution context after the operation
            clear_context()

        return result


class VapiInterface(object):
    """
    vAPI Interface class is used by the python server side bindings. This
    encapsulates the :class:`vmware.vapi.bindings.skeleton.ApiInterfaceSkeleton`
    class.
    """
    def __init__(self, api_interface, error_types=None):
        """
        Initialize the VapiInterface class

        :type  api_interface:
            :class:`vmware.vapi.bindings.skeleton.ApiInterfaceSkeleton`
        :param api_interface: Api Interface skeleton class for this interface
        :type  error_types:
            :class:`list` of :class:`vmware.vapi.bindings.type.ErrorType`
        :param error_types: error types to be registered in this configuration
        """
        self._api_interface = api_interface(self, error_types=error_types)

    @property
    def api_interface(self):
        """
        Returns the ApiInterfaceSkeleton instance. Local Provider uses this
        method to discover the ApiInterface so that it can route method calls
        for the methods implemented by this interface.

        :rtype:  :class:`vmware.vapi.bindings.skeleton.ApiInterfaceSkeleton`
        :return: Api Interface skeleton class for this interface
        """
        return self._api_interface

    @property
    def execution_context(self):
        """
        Returns the execution context of a method invocation

        :rtype: :class:`vmware.vapi.core.ExecutionContext`
        :return: Execution context of a method invocation
        """
        return get_context()
