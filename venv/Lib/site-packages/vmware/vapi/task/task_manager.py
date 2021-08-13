"""
Task Manager Interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class TaskManager(object):
    """
    The TaskManager interface providing methods to manage tasks
    """

    @abc.abstractmethod
    def create_task(self, description, service_id, operation_id,
                    cancelable, error_types, id_):
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
            :class:`vmware.vapi.data.definition.ErrorDefinition`
        :param error_types: Error definitions describing the errors this
            operation can report
        :type  id_: :class:`str`
        :param id_: Base task id
        """
        pass

    @abc.abstractmethod
    def get_info(self, task_id):
        """
        Get task info for a given task.

        :type  task_id: :class:`str`
        :param task_id: Task Id.

        :rtype:  :class:`vmware.vapi.data.value.StructValue`
        :return: Task Info
        """
        pass

    @abc.abstractmethod
    def set_info(self, task_id, info):
        """
        Set task info.

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        :type  status: :class:`vmware.vapi.data.value.StructValue`
        :param status: Task Info.
        """
        pass

    @abc.abstractmethod
    def remove_task(self, task_id):
        """
        Remove task from tasks map.

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        """
        pass

    @abc.abstractmethod
    def get_infos(self):
        """
        Get the information of all tasks.

        :rtype:  :class:`dict` of :class:`str` and
                 :class:`vmware.vapi.data.value.StructValue`
        :return: Map of task identifier to information about the task.
        """
        pass

    @abc.abstractmethod
    def mark_for_cancellation(self, task_id):
        """
        Add a task to list of tasks to be canceled.
        It depends on provider implementation to cancel it or not.

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        """
        pass

    @abc.abstractmethod
    def is_marked_for_cancellation(self, task_id):
        """
        Check whether a task is marked for cancellation.

        :type  task_id: :class:`str`
        :param task_id: Task Id.
        """
        pass
