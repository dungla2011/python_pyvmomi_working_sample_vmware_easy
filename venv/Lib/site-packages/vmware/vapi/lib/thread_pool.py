"""
This module is YATP (Yet another thread pool)
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six
import sys
import time
import threading

from six.moves import queue
from vmware.vapi.common.context import clear_event, get_event
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)
MAX_TIMEOUT = 86400  # 1 day (24*60*60 secs)


class WorkItem(object):
    """ Work item """

    def __init__(self, fn, *args, **kwargs):
        """
        Work item constructor

        :type  fn: function
        :param fn: Work item functor
        :type  args: :class:`tuple`
        :param args: Work item functor positional parameters
        :type  kwargs: :class:`dict`
        :param kwargs: Work item functor key-value parameters
        """
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.ret = None
        self.err = None
        self.event = threading.Event()

    def join(self, timeout=MAX_TIMEOUT):
        """
        Wait for work item is done

        :type  timeout: :class:`float`
        :param timeout: Timeout in seconds
        :rtype: :class:`object`
        :return: Work item functor's return value
        """
        # Wait until work is done
        self.event.wait(timeout)

        # Throw exception if error occured
        if self.err:
            raise self.err  # pylint: disable=E0702
        return self.ret

    def done(self):
        """ Signal work item is done """
        self.event.set()

    def __enter__(self):
        """
        with statement enter

        :rtype:  :class:`WorkItem`
        :return: Work item object
        """
        return self

    def __exit__(self, typ, value, traceback):
        """ with statement exit """
        self.join()
        del self.event, self.fn, self.args, self.kwargs

## Thread pool
#


class ThreadPool(object):
    """ Thread pool """

    def __init__(self, min_workers=1, max_workers=8,
                 idle_timeout=5 * 60, thread_logger=None):
        """
        Thread pool constructor

        :type   min_workers: :class:`int`
        :params min_workers: Min number of worker threads
        :type   max_workers: :class:`int`
        :params max_workers: Max number of worker threads
        :type   idle_timeout: :class:`int`
        :params idle_timeout: Worker threads idle timeout
        :type   thread_logger: :class:`logging.logger`
        :params thread_logger: logger to use. Default to stdout
        """
        assert(min_workers >= 0)
        assert(min_workers <= max_workers)
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.idle_timeout = idle_timeout
        self.workers = {}
        self.work_items = queue.Queue(0)
        self.lock = threading.Lock()
        self.shutting_down = False
        self.logger = thread_logger or logger
        for _ in range(0, self.min_workers):
            self._add_worker()

    def _log(self, msg):
        """ Log message """
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def _worker(self):
        """ Thread pool worker """
        thd_name = threading.currentThread().getName()
        while not self.shutting_down:
            try:
                # Wait for request
                try:
                    work_item = self.work_items.get(timeout=self.idle_timeout)
                except queue.Empty:
                    work_item = None

                if not work_item:
                    # Worker idle timeout. Retire thread if needed
                    self.lock.acquire()
                    try:
                        done_thread = len(self.workers) > self.min_workers
                        if done_thread:
                            self._remove_worker(thd_name)
                            break
                        else:
                            continue
                    finally:
                        self.lock.release()
                elif self.shutting_down:
                    # Put the work item back to queue
                    self.work_items.put(work_item)
                    break

                # Start work
                work_item.ret = work_item.fn(
                    *work_item.args, **work_item.kwargs)
            except:  # pylint: disable=W0702
                if sys:
                    import traceback
                    errtype, errvalue, trace = sys.exc_info()
                    stack_trace = ' '.join(traceback.format_exception(
                        errtype, errvalue, trace))
                    self._log('%s caught exception: %s'
                              % (thd_name, str(errtype)))
                    self._log(stack_trace)
                    if work_item:
                        work_item.err = errvalue

                    # In case of exception from provider also set the event
                    # so we can throw the error rightaway to client rather
                    # than waiting for the timeout to expire.
                    accept_event = get_event()
                    if accept_event is not None:
                        accept_event.set()
                        clear_event()
                    #
                    # NOTE: See the Python documentation for sys.exc_info for a
                    # warning about an inefficiency in garbage collection and
                    # the need to delete the local variable to which stacktrace
                    # is assigned
                    try:
                        del trace
                    except:  # pylint: disable=W0702
                        pass
                else:
                    # System is dying and likely to be in undefined state.
                    # sys (and other imported modules) could be unloaded and set
                    # to None when we get here. Must quit as quickly as possible
                    return

            # Signal done on work_item
            work_item.done()

        # One less worker
        self.lock.acquire()
        try:
            self._remove_worker(thd_name)
        finally:
            self.lock.release()

    def _remove_worker(self, thd_name):
        """
        Remove a worker. Assume locked

        :type  thd_name: :class:`str`
        :param thd_name: Remove a worker thread with the thread name
        """
        self.workers.pop(thd_name, None)

    def _add_worker(self):
        """ Add a worker. Assume locked """
        if len(self.workers) < self.max_workers:
            thd = threading.Thread(target=self._worker)
            thd.setDaemon(True)
            thd.start()
            self.workers[thd.getName()] = thd

    def queue_work(self, fn, *args, **kwargs):
        """
        Queue work

        Returns a work_item when work is queued to work queue
        The work will start when a ready worker is available to process the work
        User could call {work_item}.join() to wait for the work item to finish

        :type  fn: function
        :param fn: Work item functor
        :type  args: :class:`tuple`
        :param args: Work item functor positional parameters
        :type  kwargs: :class:`dict`
        :param kwargs: Work item functor key-value parameters
        :rtype: :class:`WorkItem`
        :return: work item when work is queued to work queue
        """
        if self.shutting_down:
            return None

        # Add worker if needed
        self.lock.acquire()
        try:
            self._add_worker()
        finally:
            self.lock.release()

        work_item = WorkItem(fn, *args, **kwargs)
        self.work_items.put(work_item)
        return work_item

    @staticmethod
    def normalize_works(works):
        """
        Generator to return work in normalize form: (fn, args, kwargs)

        :type  works: iteratable of fn / (fn, args) / (fn, args, kwargs)
        :param works: An iteratable of possible functor form
        :rtype: :class:`tuple` of (fn, args, kwargs)
        :return: A normalize tuple of (functor, args, kwargs)
        """
        for work in works:
            args = ()
            kwargs = {}
            if six.callable(work):
                fn = work
            elif len(work) >= 3:
                fn, args, kwargs = work
            elif len(work) == 2:
                fn, args = work
            else:
                fn = work[0]
            yield (fn, args, kwargs)

    def queue_works_and_wait(self, works):
        """
        Queue a brunch of works and wait until all works are completed / error
        out

        :type  works: iteratable of fn / (fn, args) / (fn, args, kwargs)
        :param works: An iteratable of possible functor form
        :rtype:  :class:`list` of {tuple} of :class:`bool`,:class:`object`
                 or :class:`bool`,:class:`Exception`
        :return: A list of (True, return val) / (False, exception) when all
            works done
        """
        work_items = [self.queue_work(fn, *args, **kwargs)
                      for fn, args, kwargs in self.normalize_works(works)]
        results = []
        for work in work_items:
            if work:
                try:
                    time.sleep(0.1)
                    ret = work.join()
                    results.append((True, ret))
                except:  # pylint: disable=W0702
                    results.append((False, sys.exc_info()[1]))
            else:
                # No work queued
                results.append((False, None))

        return results

    def queue_work_and_wait(self, fn, *args, **kwargs):
        """
        Queue a work and wait until the work is completed / error out

        :type  fn: function
        :param fn: Work item functor
        :type  args: :class:`tuple`
        :param args: Work item functor positional parameters
        :type  kwargs: :class:`dict`
        :param kwargs: Work item functor key-value parameters
        :rtype: :class:`tuple` of (:class:`bool`, :class:`object`) or
                (:class:`bool`, :class:`Exception`)
        :return: (True, return val) / (False, exception) when work is done
        """
        return self.queue_works_and_wait([(fn, args, kwargs)])[0]

    def shutdown(self, no_wait=False):
        """
        Shuthdown this thread pool

        :type  no_wait: :class:`bool`
        :param no_wait: Set to True to return immediately without waiting for
            all workers to quit
        """
        # Set myself as shutting down.
        if self.shutting_down:
            return
        self.shutting_down = True

        # Queue a fake work item
        work_item = object()
        self.work_items.put(work_item)

        # Wait until all workers quit
        if not no_wait:
            self._log("shutdown: Waiting for workers to quit...")
            while True:
                self.lock.acquire()
                try:
                    num_workers = len(self.workers)
                finally:
                    self.lock.release()

                # done if no worker left or not making progress
                if num_workers == 0:
                    break

                time.sleep(0.1)
            self._log("shutdown: All workers quit")

    def __del__(self):
        """ Destructor """
        self.shutdown()

    def __enter__(self):
        """ with statment enter """
        return self

    def __exit__(self, typ, value, traceback):
        """ with statment exit """
        self.shutdown()


# Thread pool instance
_thread_pool = None


def get_threadpool(max_workers=3):
    """
    Get thread pool instance.

    :type  max_workers: :class:`int`
    :param max_workers: Max number of worker threads
    """
    global _thread_pool
    if max_workers > 0 and _thread_pool is None:
        logger.info('Creating thread pool instance with %s threads',
                    max_workers)
        _thread_pool = ThreadPool(max_workers=max_workers)

    return _thread_pool
