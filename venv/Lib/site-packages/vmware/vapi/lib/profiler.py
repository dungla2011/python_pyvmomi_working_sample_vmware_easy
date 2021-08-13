"""
Convenience methods for loading the profiler
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import os


def mock_profile(func):
    """
    Mock decorator that is used when the PROFILER is not set
    """
    def wrapper(*arg, **kwargs):
        """
        Mock wrapper function
        """
        return func(*arg, **kwargs)
    return wrapper

# use profilehooks only if the PROFILER environment variable is set
perf = os.environ.get('PROFILER')
if perf == 'True':
    try:
        from profilehooks import profile  # pylint: disable=W0611
    except ImportError:
        profile = mock_profile
else:
    profile = mock_profile
