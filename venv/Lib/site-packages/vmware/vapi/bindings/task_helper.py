"""
Task helper methods
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.lib.constants import TASK_OPERATION


def is_task_operation(method_name):
    """
    Is the given operation name a task operation name

    :type  method_name: :class:`str`
    :param method_name: Method name
    :rtype: :class:`bool`
    :return: True if method name is a task operation
    """
    return method_name.endswith(TASK_OPERATION)


def get_non_task_operation_name(method_name):
    """
    Get the non task operation name of a task operation

    :type  method_name: :class:`str`
    :param method_name: Method name
    :rtype: :class:`str`
    :return: Non task operation name
    """
    return method_name.split(TASK_OPERATION)[0]


def get_task_operation_name(method_name):
    """
    Get the task operation name of an operation

    :type  method_name: :class:`str`
    :param method_name: Method name
    :rtype: :class:`str`
    :return: Task operation name
    """
    return '%s%s' % (method_name, TASK_OPERATION)
