"""
Common REST classes/lib
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import six


class OperationRestMetadata(object):
    """
    This class holds the metadata for making a REST request

    :type http_method: :class:`str`
    :ivar http_method: HTTP method
    :type request_body_parameter: :class:`str`
    :ivar request_body_parameter: Python runtime name of the parameter that
                                  forms the HTTP request body
    """
    def __init__(self, http_method, url_template='',
                 request_body_parameter=None, path_variables=None,
                 query_parameters=None, dispatch_parameters=None,
                 header_parameters=None, dispatch_header_parameters=None,
                 content_type=None):
        """
        Initialze the rest metadata class

        :type  http_method: :class:`str`
        :param http_method: HTTP method
        :type  url_template: :class:`str`
        :param url_template: URL path template
        :type  path_variables: :class:`dict` of :class:`str` and :class:`str`
        :param path_variables: Map of python runtime name and the path
                               variable name used in the URL template
        :type  query_parameters: :class:`dict` of :class:`str` and :class:`str`
        :param query_parameters: Map of python runtime name and query parameter
                                 name
        :type  request_body_parameter: :class:`str`
        :param request_body_parameter: Python runtime name of the parameter that
                                       forms the HTTP request body
        :type  dispatch_parameters: :class:`str`
        :param dispatch_parameters: Map of query parameter wit its value
                                    defined in interface Verb annotation
        :type  header_parameters: :class:`str`
        :param header_parameters: Map of header name with variable name
        :type  dispatch_header_parameters: :class:`str`
        :param dispatch_header_parameters: Map of header name with its value
                                           defined in interface Verb annotation
        """
        self.http_method = http_method
        self._url_template = url_template
        self.request_body_parameter = request_body_parameter
        self._path_variables = (
            path_variables if path_variables is not None else {})
        self._query_parameters = (
            query_parameters if query_parameters is not None else {})
        self._dispatch_parameters = (
            dispatch_parameters if dispatch_parameters is not None else {})
        self._header_parameters = (
            header_parameters if header_parameters is not None else {})
        self._dispatch_header_parameters = (
            dispatch_header_parameters if dispatch_header_parameters is not None else {})  # pylint: disable=line-too-long
        self.content_type = content_type

    def get_url_path(self, path_variable_fields, query_parameter_fields):
        """
        Get the final URL path by substituting the actual values in the template
        and adding the query parameters

        :type  path_variable_fields: :class:`dict` of :class:`str` and
                                     :class:`str`
        :param path_variable_fields: Map of python runtime name for URL path
                                     variable and its value
        :type  query_parameter_fields: :class:`dict` of :class:`str` and
                                       :class:`str`
        :param query_parameter_fields: Map of python runtime name for query
                                       parameter variable and its value
        :rtype: :class:`unicode` for Python 2 and :class:`str` for Python 3
        :return: URL path
        """
        url_path = six.text_type(self._url_template)

        # Substitute path variables with values in the template
        for (field_name, field_str) in six.iteritems(
                path_variable_fields):
            url_path = url_path.replace('{%s}'
                                        % self._path_variables[field_name],
                                        field_str)
        # Construct the query params portion of the url
        query_parameter_str = '&'.join([
            '%s=%s' % (self._query_parameters[field_name], field_str)
            for (field_name, field_str)
            in six.iteritems(query_parameter_fields)])
        if query_parameter_str:
            # Append the query params portion if it exists
            connector = '?' if '?' not in url_path else '&'
            url_path = connector.join([url_path, query_parameter_str])
        if not bool(self._dispatch_parameters):
            # Append the dispatch parameters not in query params
            dispatch_parameters_str = '&'.join([
                '%s=%s' % (self._dispatch_parameters[field_name], field_str)
                for (field_name, field_str)
                in six.iteritems(self._dispatch_parameters)])
            url_path = url_path + dispatch_parameters_str

        return url_path

    def get_path_variable_field_names(self):
        """
        Get the list of field names used in the URL path template

        :rtype: :class:`list` of :class:`str`
        :return: List of fields used in the URL path template
        """
        if six.PY2:
            return list(self._path_variables.viewkeys())
        else:
            return list(self._path_variables.keys())

    def get_query_parameter_field_names(self):
        """
        Get the list of field names used as query parameters

        :rtype: :class:`list` of :class:`str`
        :return: List of fields used as query parameters
        """
        if six.PY2:
            return list(self._query_parameters.viewkeys())
        else:
            return list(self._query_parameters.keys())

    def get_header_field_names(self):
        """
        Get the list of field names used as headers

        :rtype: :class:`list` of :class:`str`
        :return: List of fields used as header
        """
        if six.PY2:
            return list(self._header_parameters.viewkeys())
        else:
            return list(self._header_parameters.keys())

    def get_dispatch_header(self):
        """
        Get the map of field names and value as dispatch headers

        :rtype: :class:`list` of :class:`str`
        :return: Map of name and value as dispatch header
        """
        return self._dispatch_header_parameters
