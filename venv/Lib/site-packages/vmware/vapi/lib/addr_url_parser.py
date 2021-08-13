"""
vAPI configuration addr url parser
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import sys

from six.moves import urllib

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


def parse_addr_url(url):
    """
    Parse addr url (as described in http://www.rabbitmq.com/uri-spec.html)
    Note: This fn make no attempt to unescape the url, just like the urlparse

    :type  url: :class:`str`
    :param url: The addr url to parse

    :rtype:  :class:`tuple` of (scheme, host, port, user, password, path, query_dict)\
             where scheme: url scheme
                   host: hostname
                   port: query_dict is a dictionary of (name, [values])
    :return: Parsed addr url
    """

    scheme = None
    host, port = None, None
    user, password = None, None
    path = None
    query_dict = None

    # Use urlparse first to parse the url, but it failed to parse amqp[s]
    # NYI: RFC3986 re ?
    if url:
        # urlparse returns a named dict. Need to disable pylint E1101
        # or else we have tons of warning with result.xxx
        # pylint: disable=E1101
        result = urllib.parse.urlparse(url)
        scheme = result.scheme
        netloc = result.netloc
        if result.path:
            path = result.path
        if sys.version_info[:2] < (2, 7):
            # Older version of python failed to parse netloc and put everything in
            # result.path. Do a manual parse
            if result.path.startswith('//'):
                idx = result.path[2:].find('/')
                if idx >= 0:
                    netloc += result.path[2:idx + 2]
                    path = result.path[idx + 2:]
                else:
                    netloc += result.path[2:]
                    path = None

        if netloc:
            # Parse user:passwd@...
            tokens = netloc.split('@', 1)
            if len(tokens) > 1:
                user_info, host_info = tokens[:2]
                tokens = user_info.split(':', 1)
                if len(tokens) > 1:
                    user, password = tokens[:2]
                else:
                    user, password = tokens[0], None
            else:
                user, password = None, None
                host_info = tokens[0]

            # Parse host [ ':' port ]
            # Check for ipv6 addr
            tokens = []
            if len(host_info) >= 2 and host_info[0] == '[':
                idx = host_info.find(']')
                if idx != -1:
                    tokens.append(host_info[0:idx + 1])
                    port = host_info[idx + 1:]
                    idx = port.rfind(':')
                    if idx != -1:
                        tokens.append(port[idx + 1:])
                else:
                    # Incomplete ipv6 addr...
                    logger.error('Invalid ipv6 addr: %s', url)
            else:
                tokens = host_info.rsplit(':', 1)

            if len(tokens) > 1:
                if tokens[0]:
                    host, port = tokens[:2]
                else:
                    port = tokens[1]
                try:
                    port = int(port)
                except ValueError:
                    logger.error('Invalid port number: %s', url)
                    port = None
            elif tokens[0]:
                host, port = tokens[0], None

        # Parse path queries
        if path:
            tokens = path.split('?', 1)
            if len(tokens) > 1:
                path, queries = tokens[:2]
            else:
                path, queries = tokens[0], result.query
            if queries:
                query_dict = urllib.parse.parse_qs(queries)

    return scheme, host, port, user, password, path, query_dict


def get_url_scheme(url):
    """
    Get the scheme from the url (as described in http://www.rabbitmq.com/uri-spec.html)

    :type  url: :class:`str`
    :param url: The addr url to parse

    :rtype:  :class:`str`
    :return: url scheme
    """
    return parse_addr_url(url)[0]
