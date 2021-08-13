"""
Factory methods for creating application context
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import uuid

from vmware.vapi.common.context import get_context
from vmware.vapi.core import ApplicationContext
from vmware.vapi.lib.constants import OPID, TASK_ID


def create_operation_id():
    """
    Create a new operation id. It is a randomly generated uuid

    :rtype: :class:`str`
    :return: Newly created operation id
    """
    return str(uuid.uuid4())


def create_default_application_context():
    """
    Create a default application context. The
    created context will only have opId.

    :rtype: :class:`vmware.vapi.core.ApplicationContext`
    :return: Newly created application context
    """
    return ApplicationContext({OPID: create_operation_id()})


def insert_operation_id(app_ctx):
    """
    Add an operation id to the application context if there is none present.
    If an operation id is present, then this is a no op.

    :type app_ctx: :class:`vmware.vapi.core.ApplicationContext`
    :param app_ctx: Application context
    """
    if app_ctx and OPID not in app_ctx:
        app_ctx.setdefault(OPID, create_operation_id())


def insert_task_id(app_ctx, task_id):
    """
    Add a task id to the application context.

    :type app_ctx: :class:`vmware.vapi.core.ApplicationContext`
    :param app_ctx: Application Context
    :type task_id: :class:`str`
    :param task_id: Task Id
    """
    if app_ctx is not None:
        app_ctx[TASK_ID] = task_id


def remove_task_id(app_ctx):
    """
    Remove a task id from the application context.

    :type app_ctx: :class:`vmware.vapi.core.ApplicationContext`
    :param app_ctx: Application Context
    """
    if app_ctx is not None:
        app_ctx.pop(TASK_ID, None)


def get_task_id():
    """
    Return task id stored in application context.
    Return None if there's no task id present.

    :rtype: :class:`str`
    :return: Task Id
    """
    ctx = get_context()
    if ctx is not None:
        app_ctx = ctx.application_context
        if app_ctx:
            return app_ctx.get(TASK_ID)

    return None


def insert_header(app_ctx, key, value):
    """
    Add a key, value pair in application context.
    If the key exists override the value.

    :type  app_ctx: :class:`vmware.vapi.core.ApplicationContext`
    :param app_ctx: Application Context
    :type  key: :class:`str`
    :param key: Application context key
    :type  value: :class:`str`
    :param value: Application context key value
    """
    if app_ctx is not None:
        app_ctx[key] = value
