"""
Workers thread pool
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

_workers_pool = {}


def get_workers_pool(pool_tag):
    """
    get workers pool

    :type  pool_tag: :class:`str`
    :param pool_tag: workers pool tag
    :rtype: :class:`vmware.vapi.lib.thread_pool.ThreadPool`
    :return: workers pool
    """
    global _workers_pool  # pylint: disable=W0602
    pool = _workers_pool.get(pool_tag)
    if not pool:
        from vmware.vapi.lib.thread_pool import ThreadPool
        pool = ThreadPool(max_workers=8)
        _workers_pool[pool_tag] = pool
    return pool
