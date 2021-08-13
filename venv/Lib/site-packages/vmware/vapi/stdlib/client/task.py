"""
Task Helper for clients
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.bindings.converter import TypeConverter


class Task(object):
    """
    Task Helper class for clients
    """
    def __init__(self, task_id, task_svc_instance, result_type):
        """
        Initialize the Task Helper class

        :type  task_id: :class:`str`
        :param task_id: Task Id
        :type  task_svc_instance: :class:`com.vmware.cis_client.Tasks`
        :param task_svc_instance: Task Service instance
        :type  result_type: :class:`vmware.vapi.bindings.BindingType`
        :param result_type: Result type
        """
        self.task_id = task_id
        self.task_svc_instance = task_svc_instance
        self.result_type = result_type

    def _get_task_svc_instance(self):
        """
        Returns tasks service instance

        :rtype: :class:`com.vmware.cis_client.Tasks`
        :return: Tasks service instance
        """
        return self.task_svc_instance

    def get_task_id(self):
        """
        Returns task id

        :rtype: :class:`str`
        :return: Task Id
        """
        return self.task_id

    def get_info(self):
        """
        Returns tasks info

        :rtype: :class:`com.vmware.cis.tasks_client.Info`
        :return: Task Info
        """
        return self.task_svc_instance.get(self.task_id)

    def get_result(self):
        """
        Returns task result

        :rtype: :class:`com.vmware.cis.tasks_client.Info`
        :return: Task Result
        """
        info = self.get_info()
        if hasattr(info, 'result'):
            return TypeConverter.convert_to_python(info.result,
                                                   self.result_type)
        else:
            return None

    def get_error(self):
        """
        Returns task error

        :rtype: :class:`Exception`
        :return: Task Error
        """
        return self.get_info().error
