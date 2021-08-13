"""
Msg based protocol handler
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from collections import deque

from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.protocol.server.api_handler import ApiHandler, AsyncApiHandler
from vmware.vapi.protocol.server.transport.async_protocol_handler import AsyncProtocolHandler

logger = get_vapi_logger(__name__)


def get_async_api_handler(api_handler):
    """
    get async api handler

    :type  api_handler: :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
    :param api_handler: api handler instance
    :rtype:  :class:`vmware.vapi.protocol.server.async_api_handler_adapter.PooledAsyncApiHandlerAdapter`
    :return: Threaded async api handler
    """
    if isinstance(api_handler, ApiHandler):
        from vmware.vapi.protocol.server.async_api_handler_adapter import PooledAsyncApiHandlerAdapter
        from vmware.vapi.lib.workers_pool import get_workers_pool
        workers_pool = get_workers_pool('api_handler')
        api_handler = PooledAsyncApiHandlerAdapter(api_handler, workers_pool)
    return api_handler


class MsgBasedProtocolHandler(AsyncProtocolHandler):
    """ Message based protocol handler """
    def __init__(self, api_handler):
        """
        Message based protocol handler init
        :type  api_handler: :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
        :param api_handler: api handler instance
        """
        AsyncProtocolHandler.__init__(self)
        assert(api_handler)
        self.api_handler = get_async_api_handler(api_handler)

    ## Begin AsyncProtocolHandler interface

    def get_data_handler(self, connection):
        data_handler = self.DataHandler(self, connection)
        return data_handler

    ## End AsyncProtocolHandler interface

    class DataHandler(AsyncProtocolHandler.DataHandler):
        """ Message based protocol data handler """
        def __init__(self, parent, connection):
            """ Message based protocol data handler init """
            AsyncProtocolHandler.DataHandler.__init__(self)
            self.parent = parent
            self.connection = connection
            self.data = deque()

        ## Begin AsyncProtocolHandler.DataHandler interface

        def data_ready(self, data):
            if data:
                self.data.append(data)

        def data_end(self):
            connection = self.connection

            def state_change_cb(*args, **kwargs):
                """ state change callback """
                self.request_state_change(connection, *args, **kwargs)

            self.parent.api_handler.async_handle_request(
                b''.join(self.data), state_change_cb)
            self._cleanup()

        def data_abort(self):
            self._cleanup()

        # Used to throttle the lower layer from sending more data
        def can_read(self):
            # TODO: Throttle if needed
            return True

        ## End AsyncProtocolHandler.DataHandler interface
        def request_state_change(self, connection, state, response=None):  # pylint: disable=R0201
            """
            request state changed

            :type  connection: :class:`file`
            :param connection: response connection
            :type  state: :class:`int`
            :param state: refer to :class:`vmware.vapi.protocol.server.api_handler.\
                            AsyncApiHandler.async_handle_request` state_change_cb
            :type  response: :class:`object`
            :param response: refer to :class:`vmware.vapi.protocol.server.api_handler.\
                                AsyncApiHandler.async_handle_request` state_change_cb
            """

            if state in AsyncApiHandler.END_STATES:
                # Reached one of the end state
                try:
                    if state == AsyncApiHandler.SUCCESS:
                        try:
                            connection.write(response)
                        except Exception as err:
                            # Connection closed
                            logger.error('write: Failed to write %s', err)
                    elif state == AsyncApiHandler.ERROR:
                        if response is None:
                            response = Exception("Error")
                        raise response  # pylint: disable=E0702
                    elif state == AsyncApiHandler.CANCELLED:
                        # Cancelled
                        pass
                    else:
                        # Unexpected state
                        raise NotImplementedError('Unexpected state %d' % state)
                finally:
                    connection.close()   # Close the virtual connection
                    connection = None
            else:
                # Transition state change
                pass

        def _cleanup(self):
            """ Cleanup """
            self.data = None
            self.connection = None
            self.parent = None

        def __del__(self):
            self._cleanup()
