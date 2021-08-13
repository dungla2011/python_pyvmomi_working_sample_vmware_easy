"""
Task Handle interface for publishing task info
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from com.vmware.vapi.std_provider import LocalizableMessage
from vmware.vapi.bindings.type import BooleanType, StringType
from vmware.vapi.bindings.converter import TypeConverter
from vmware.vapi.common.context import get_event, clear_event
from vmware.vapi.data.definition import OpaqueDefinition
from vmware.vapi.data.value import OptionalValue
from vmware.vapi.exception import CoreException
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.context import get_task_id
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.std import make_error_value_from_msgs, make_std_error_def
from vmware.vapi.task.task_manager_impl import (get_task_manager,
                                                FAILED_STRING_VALUE)

logger = get_vapi_logger(__name__)


class TaskHandle(object):
    """
    The TaskHandle interface for publishing task info.
    This class is not thread safe. Info returned from the get is mutable.
    Task method will not return task ID to client until provider calls publish
    method with accept=True once.
    Provider must call publish to save the updates to task state into
    TaskManager.
    """

    _internal_server_error_def = make_std_error_def(
            'com.vmware.vapi.std.errors.internal_server_error')

    def __init__(self, info_type, result_type):
        self.task_manager = get_task_manager()
        self.info_type = info_type
        self.result_type = result_type
        self.error_types = []
        self.task_id = get_task_id()
        self.info = info_type()
        self._initialize_common_info()

    def _initialize_common_info(self):
        """
        Initialize common task info fields
        """
        summary = self.task_manager.get_summary(self.task_id)
        published_info = summary.info
        self.error_types = summary.errors
        self._override_api_info(published_info)
        self.info.cancelable = TypeConverter.convert_to_python(
                                    published_info.get_field('cancelable'),
                                    BooleanType())
        desc = published_info.get_field('description')
        if desc is not None:
            self.info.description = TypeConverter.convert_to_python(
                                        desc,
                                        LocalizableMessage.get_binding_type())
        self.info.status = TypeConverter.convert_to_python(
                                published_info.get_field('status'),
                                StringType())

        try:
            user = published_info.get_field('user')
            self.info.user = TypeConverter.convert_to_python(
                                user,
                                StringType())
        except:  # pylint: disable=W0702
            pass

    def _override_api_info(self, published_info):
        """
        Override service and operation task info fields
        """
        self.info.service = TypeConverter.convert_to_python(
                                published_info.get_field('service'),
                                StringType())
        self.info.operation = TypeConverter.convert_to_python(
                                published_info.get_field('operation'),
                                StringType())

    def get_info(self):
        """
        Returns the Task Info.
        """
        return self.info

    def get_published_info(self):
        """
        Returns the current published task Info
        """
        info = self.task_manager.get_info(self.task_id)
        converted_info = TypeConverter.convert_to_python(
                            info,
                            self.info_type.get_binding_type())
        return converted_info

    def publish(self, accept=False):
        """
        Publish the temporary task info into task manager

        :type  accept: :class:`bool`
        :param accept: Accept task and return task id to client
        """
        msg_list = None
        published_info = self.task_manager.get_info(self.task_id)

        # Override the common info fields which can't be modified by providers
        self._override_api_info(published_info)

        if hasattr(self.info, 'error') and self.info.error is not None:
            err_type = self.info.error.get_binding_type()
            # Verify if the error set by provider is amongst the ones
            # defined in VMODL2, if not throw InternalServerError
            if (err_type not in self.error_types):
                msg_list = [message_factory.get_message(
                            'vapi.task.invalid.error',
                            err_type.name,
                            self.info.operation)]

        if hasattr(self.info, 'result') and self.info.result is not None:
            # Check if result type is Opaque or actual type
            res_type = self.info_type.get_binding_type().get_field('result')
            if isinstance(res_type.element_type.definition, OpaqueDefinition):
                result = None
                try:
                    result = TypeConverter.convert_to_vapi(
                                self.info.result,
                                self.result_type.get_binding_type())
                except AttributeError:
                    try:
                        result = TypeConverter.convert_to_vapi(self.info.result,
                                                               self.result_type)
                    except CoreException:
                        msg_list = [message_factory.get_message(
                                    'vapi.task.invalid.result',
                                    self.info.result,
                                    self.info.operation)]
                        self.info.result = None

                if msg_list is None:
                    self.info.result = result

        info = TypeConverter.convert_to_vapi(
                    self.info,
                    self.info_type.get_binding_type())

        if msg_list is not None:
            info.set_field('status', FAILED_STRING_VALUE)
            logger.error(msg_list[0])
            error = make_error_value_from_msgs(
                        self._internal_server_error_def, *msg_list)
            info.set_field('error', OptionalValue(error))

        self.task_manager.set_info(self.task_id, info)

        if accept:
            event = get_event()
            event.set()
            clear_event()
            # Validate that description is set while accepting the task
            desc = self.info.description
            if desc is None or (not desc.id and not desc.default_message):
                msg = message_factory.get_message(
                        'vapi.data.structure.field.missing',
                        self.info_type, 'description')
                logger.debug(msg)
                raise CoreException(msg)

    def is_marked_for_cancellation(self):
        """
        Check whether a task is marked for cancellation.
        """
        return self.task_manager.is_marked_for_cancellation(self.task_id)


def get_task_handle(info_type, result_type):
    """
    Creates and returns the TaskHandle instance

    :type  info_type: :class:`com.vmware.cis.task_provider.Info`
    :param info_type: Task Info class.
    :type  result_type: :class:`com.vmware.cis.task_provider.Result`
    :param result_type: Result type.
    """
    return TaskHandle(info_type, result_type)
