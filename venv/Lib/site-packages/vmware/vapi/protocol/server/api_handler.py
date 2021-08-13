"""
Api handler interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class ApiHandler(object):
    """ Generic api handler interface """

    def __init__(self):
        """ Generic api handler interface init """

    def handle_request(self, request, headers=None):
        """
        handle request

        :type:  :class:`str`
        :param: request string
        :type:  :class:`dict`
        :param: Request headers
        :rtype: :class:`str`
        :return: response string
        """
        raise NotImplementedError


class AsyncApiHandler(ApiHandler):
    """ Callback based AsyncApiHandler """

    # Current states
    (SUCCESS, ERROR, PENDING, CANCELLED) = (1 << 0, 1 << 1, 1 << 2, 1 << 3)
    VALID_STATES = (SUCCESS, ERROR, PENDING, CANCELLED)
    END_STATES = (SUCCESS, ERROR, CANCELLED)

    def __init__(self):
        """ Callback based AsyncApiHandler init """
        ApiHandler.__init__(self)

    def async_handle_request(self, request, state_change_cb=None):
        """
        async handle request

        :type  request: :class:`str`
        :param request: request string
        :type  state_change_cb: function
        :param state_change_cb: state change callback
          def state_change_cb(state,    # One of the valid state
                              response) # Response value associated with state
            # SUCCESS: response is the request response msg
            # ERROR: response is the exception thrown (or error response msg?)
            # PENDING: response is the progress (0 - 100)
            # CANCELLED: None
        """
        raise NotImplementedError
