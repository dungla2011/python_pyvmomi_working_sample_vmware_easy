"""
Async api handler adapter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.protocol.server.api_handler import AsyncApiHandler
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class PooledAsyncApiHandlerAdapter(AsyncApiHandler):
    """ Pooled async api handler adapter """
    def __init__(self, api_handler, workers_pool):
        """
        Pooled async api handler adapter init

        :type  api_handler: :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
        :param api_handler: api handler
        :type  workers_pool: :class:`object` with function 'queue_work'.
                e.g. :class:`vmware.vapi.lib.thread_pool.ThreadPool`
        :param workers_pool: worker pool object
        """
        AsyncApiHandler.__init__(self)
        self.handler = api_handler
        self.workers_pool = workers_pool

    def async_handle_request(self, request, state_change_cb=None):
        def do_work():
            """ do work """
            try:
                response = self.handler.handle_request(request)
                if state_change_cb:
                    state_change_cb(self.SUCCESS, response)
            except Exception as err:
                import traceback
                stack_trace = traceback.format_exc()
                logger.critical(stack_trace)
                if state_change_cb:
                    state_change_cb(self.ERROR, err)
        self.workers_pool.queue_work(do_work)

    def handle_request(self, request):
        raise NotImplementedError
