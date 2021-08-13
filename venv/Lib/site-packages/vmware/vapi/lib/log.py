"""
Helper functions for configuring logging in vapi runtime
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2016-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import logging

from vmware.vapi.common.context import get_context

NO_OP_ID_MSG = 'No-Op-id'


# TODO Remove this once all move to using new client logger
def get_raw_request_logger():
    """
    Return the raw request logger that is not propagated to root logger and
    disabled by default.
    :rtype: :class:`logging.Logger`
    :return: Raw request logger
    """
    return _client_wire_logger


def get_client_wire_logger():
    """
    Return the client wire logger that is not propagated to root logger and
    disabled by default. It is used to log raw wire request/responses
    :rtype: :class:`logging.Logger`
    :return: Raw request logger
    """
    return _client_wire_logger


def get_provider_wire_logger():
    """
    Return the provider wire logger that is not propagated to root logger and
    disabled by default. It is used to log raw wire request/responses
    :rtype: :class:`logging.Logger`
    :return: Raw request logger
    """
    return _provider_wire_logger


class VapiFilter(logging.Filter):
    """
    This is a filter that injects operation id into the log record
    """
    def filter(self, record):
        ctx = get_context()
        if ctx is not None:
            record.op_id = ctx.application_context.get('opId')
        else:
            record.op_id = NO_OP_ID_MSG
        return True

# Single filter instance that should be attached to all the loggers in vapi
# runtime
_vapi_filter = VapiFilter()


def get_vapi_logger(logger_name):
    """
    Return a logger that is compatible with the VAPI provider log formats.
    Currently, it only adds the VapiFilter

    :rtype: :class:`logging.Logger`
    :return: Vapi provider logger
    """
    logger = logging.getLogger(logger_name)
    logger.addFilter(_vapi_filter)
    return logger

PROVIDER_WIRE_LOGGER_NAME = '%s.provider.wirelogging' % __name__
CLIENT_WIRE_LOGGER_NAME = '%s.client.wirelogging' % __name__

_client_wire_logger = get_vapi_logger(CLIENT_WIRE_LOGGER_NAME)

# Turn off propagation so that the log events do not reach parent handlers.
_client_wire_logger.propagate = False

# Add a null handler otherwise logging will complain that no handlers are
# configured. Typically root logger has handlers configured and each logger in
# the hierarchy gets those handlers too due to propagation.
_client_wire_logger.addHandler(logging.NullHandler())

_provider_wire_logger = get_vapi_logger(PROVIDER_WIRE_LOGGER_NAME)

# Turn off propagation so that the log events do not reach parent handlers.
_provider_wire_logger.propagate = False

# Add a null handler otherwise logging will complain that no handlers are
# configured. Typically root logger has handlers configured and each logger in
# the hierarchy gets those handlers too due to propagation.
_provider_wire_logger.addHandler(logging.NullHandler())
