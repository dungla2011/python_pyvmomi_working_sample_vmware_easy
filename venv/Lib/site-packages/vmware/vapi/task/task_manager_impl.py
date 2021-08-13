"""
Task Manager Interface Implementation
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from datetime import datetime
import threading
import uuid
from com.vmware.vapi.std_provider import LocalizableMessage
from vmware.vapi.bindings.converter import TypeConverter
from vmware.vapi.common.context import get_context
from vmware.vapi.data.value import (BooleanValue, ListValue,
                                    StringValue, StructValue)
from vmware.vapi.lib.constants import AUTHN_IDENTITY
from vmware.vapi.task.task_manager import TaskManager

URI_DELIMITER = ':'
TASK_EXPIRE_DURATION_SEC = 24 * 60 * 60
PENDING_STRING_VALUE = StringValue('PENDING')
SUCCEEDED_STRING_VALUE = StringValue('SUCCEEDED')
FAILED_STRING_VALUE = StringValue('FAILED')
TRUE_BOOLEAN_VALUE = BooleanValue(True)


class TaskSummary(object):
    """
    TaskSummary class to store task info, operation output type
    and error types
    """
    def __init__(self, info, errors):
        self.info = info
        self.errors = [error.resolved_type for error in errors]

    def __repr__(self):
        args = (repr(self.info),
                repr(self.errors))
        return 'TaskSummary(info=%s, errors=%s)' % args


class TaskManagerImpl(TaskManager):
    """
    The TaskManager interface implementation providing methods to manage tasks
    """
    def __init__(self):
        # map of task_id to task summary
        self.task_map = {}

        # tasks_to_remove contains list of (task_id,
        # last status change time stamp)
        self.tasks_to_remove = set()

        # tasks_to_cancel contains set of tasks being marked canceled
        self.tasks_to_cancel = set()
        self.lock = threading.RLock()
        TaskManager.__init__(self)

    def create_task(self, description, service_id, operation_id,
                    cancelable, error_types, id_=None):
        """
        Creates a task in task manager.

        :type  description: :class:`com.vmware.vapi.std.LocalizableMessage`
        :param description: Task description.
        :type  service_id: :class:`str`
        :param service_id: Service Id.
        :type  operation_id: :class:`str`
        :param operation_id: Operation Id.
        :type  cancelable: :class:`bool`
        :param cancelable: Is the task cancelable.
        :type  error_types: :class:`list` of
            :class:`vmware.vapi.bindings.type.ReferenceType`
        :param error_types: Error definitions describing the errors this
            operation can report
        :type  id_: :class:`str`
        :param id_: Base task id
        """
        task_info = StructValue()
        if description is not None:
            task_info.set_field(
                'description', TypeConverter.convert_to_vapi(
                                    description,
                                    LocalizableMessage.get_binding_type()))
        else:
            desc_value = StructValue()
            desc_value.set_field('id', StringValue())
            desc_value.set_field('default_message', StringValue())
            desc_value.set_field('args', ListValue())
            task_info.set_field('description', desc_value)

        user = self._get_user_from_sec_ctx()
        if user is not None:
            task_info.set_field('user', StringValue(user))

        task_info.set_field('service', StringValue(service_id))
        task_info.set_field('operation', StringValue(operation_id))
        task_info.set_field('cancelable',
                            BooleanValue(True if cancelable else False))
        task_info.set_field('status', PENDING_STRING_VALUE)
        base_id = id_ if id_ is not None else str(uuid.uuid4())
        task_id = self._create_task_id(base_id, service_id)

        task_summary = TaskSummary(task_info, error_types)
        with self.lock:
            self.task_map.setdefault(task_id, task_summary)

        self._remove_expired_task()
        return task_id

    def get_summary(self, task_id):
        """
        Get task summary.

        :type  task_id: :class:`str`
        :param task_id: Task Id.

        :rtype:  :class:`vmware.vapi.task.task_manager_impl.TaskSummary`
        :return: Task Summary
        """
        return self.task_map[task_id]

    def get_info(self, task_id):
        """
        Get task info.

        :type  task_id: :class:`str`
        :param task_id: Task Id.

        :rtype:  :class:`vmware.vapi.data.value.StructValue`
        :return: Task Info
        """
        return self.task_map[task_id].info

    def set_info(self, task_id, info):
        """
        Set task info.

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        :type  status: :class:`vmware.vapi.data.value.StructValue`
        :param status: Task Info.
        """
        self.task_map[task_id].info = info
        if info.get_field('status') in [SUCCEEDED_STRING_VALUE,
                                        FAILED_STRING_VALUE]:
            with self.lock:
                self.tasks_to_remove.add((task_id, datetime.utcnow()))
                self.tasks_to_cancel.discard(task_id)

    def _create_task_id(self, base_id, service_id):
        """
        Create task id.

        :type  base_id: :class:`str`
        :param base_id: Task Id.
        :type  service_id: :class:`str`
        :param service_id: Service ID
        """
        return '%s%s%s' % (base_id, URI_DELIMITER, service_id)

    def _get_user_from_sec_ctx(self):
        """
        Get user name from security context.

        :rtype:  :class:`str`
        :return: User name
        """
        exec_ctx = get_context()

        if exec_ctx is not None:
            sec_ctx = get_context().security_context
            if sec_ctx is not None:
                identity = sec_ctx.get(AUTHN_IDENTITY)
                if identity is not None:
                    return identity.get_username()
        return None

    def remove_task(self, task_id):
        """
        Remove task from tasks map
        """
        with self.lock:
            self.task_map.pop(task_id, None)

    def _remove_expired_task(self):
        """
        Remove expired tasks from the task map
        """
        with self.lock:
            curr_time = datetime.utcnow()
            tasks_list = set(self.tasks_to_remove)
            for task_id, t in tasks_list:
                time_elapsed = curr_time - t
                if (time_elapsed.total_seconds() < TASK_EXPIRE_DURATION_SEC):
                    break
                self.tasks_to_remove.remove((task_id, t))
                # Avoid KeyError for missing task_id
                self.task_map.pop(task_id, None)

    def get_infos(self):
        """
        Get the information of all tasks.

        :rtype:  :class:`dict` of :class:`str` and
                 :class:`vmware.vapi.data.value.StructValue`
        :return: Map of task identifier to information about the task.
        """
        # Create a map of task id to task infos to return
        task_info_map = {key: val.info for key, val in self.task_map.items()}
        return task_info_map

    def mark_for_cancellation(self, task_id):
        """
        Add the task to list of tasks to be canceled

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        """
        info = self.get_info(task_id)
        if info.get_field('cancelable') == TRUE_BOOLEAN_VALUE:
            with self.lock:
                self.tasks_to_cancel.add(task_id)

    def is_marked_for_cancellation(self, task_id):
        """
        Check whether a task is marked for cancellation.

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        """
        return task_id in self.tasks_to_cancel


# Task manager instance
_task_manager = None


def get_task_manager(task_manager=None):
    """
    Returns the singleton task manager instance

    :type:  :class:`str`
    :param: Task manager class
    """
    global _task_manager
    if _task_manager is None:
        if task_manager is None:
            _task_manager = TaskManagerImpl()
        else:
            _task_manager = task_manager()

    return _task_manager


def delete_task_manager():
    """
    Reset task manager singleton instance to None
    This method is to be used mainly by tests
    """
    global _task_manager
    _task_manager = None
