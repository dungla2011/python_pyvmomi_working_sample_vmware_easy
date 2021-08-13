"""
Core Protocol Definition classes
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class ApiProvider(object):
    """
    The ApiProvider interface is used for invocation of operations
    """
    @abc.abstractmethod
    def invoke(self, service_id, operation_id, input_value, ctx):
        """
        Invokes the specified method using the input value and the
        the execution context provided

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Input parameters for the method
        :type  ctx: :class:`ExecutionContext`
        :param ctx: Execution context for the method

        :rtype: :class:`MethodResult`
        :return: Result of the method invocation
        """

    def __hash__(self):
        return str(self).__hash__()


class ApiInterface(object):
    """
    The ApiInterface interface provides introspection APIs for a
    vAPI interface; it is implemented by API providers.
    """
    # Interface class, don't need to warn about unused argument / method
    # could be function
    # pylint: disable=W0613,R0201
    def __init__(self):
        """
        Initialize the Api Interface instance
        """

    def get_identifier(self):
        """
        Returns interface identifier

        :rtype: :class:`InterfaceIdentifier`
        :return: Interface identifier
        """
        raise NotImplementedError

    def get_definition(self):
        """
        Returns interface definition

        :rtype: :class:`InterfaceDefinition`
        :return: Interface definition
        """
        raise NotImplementedError

    def get_method_definition(self, method_id):
        """
        Returns the method definition

        :rtype: :class:`MethodDefinition`
        :return: Method definition
        """
        raise NotImplementedError

    def invoke(self, ctx, method_id, input_value):
        """
        Invokes the specified method using the execution context and
        the input provided

        :type  ctx: :class:`ExecutionContext`
        :param ctx: Execution context for this method
        :type  method_id: :class:`MethodIdentifier`
        :param method_id: Method identifier
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters

        :rtype: :class:`MethodResult`
        :return: Result of the method invocation
        """
        raise NotImplementedError

    def __hash__(self):
        return str(self).__hash__()


class InterfaceIdentifier(object):
    """
    InterfaceIdentifier has the information required to uniquely
    address a vAPI interface
    """
    def __init__(self, iface):
        """
        Initialize an InterfaceIdentifier

        :type  iface: :class:`str`
        :param iface: String identifier of the interface
        """
        self.iface = str(iface)

    def get_name(self):
        """
        Returns the string identifier of the interface

        :rtype: :class:`str`
        :return: String identifier of the interface
        """
        return self.iface

    def __eq__(self, other):
        return (isinstance(other, InterfaceIdentifier)
                and self.iface == other.iface)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'InterfaceIdentifier(%s)' % repr(self.iface)

    def __hash__(self):
        return str(self).__hash__()


class MethodIdentifier(object):
    """
    This class identifies a :class:`ApiMethod` instance
    """
    def __init__(self, iface, method):
        """
        Initialize the MethodIdentifier

        :type  iface: :class:`InterfaceIdentifier`
        :param iface: InterfaceIdentifier of this method
        :type  method: :class:`str`
        :param method: String identifier of this method
        """
        if not isinstance(iface, InterfaceIdentifier):
            raise TypeError('Expected argument of type InterfaceIdentifier,'
                            'but got %s' % type(iface).__name__)
        self.iface = iface
        if not isinstance(method, six.string_types):
            raise TypeError('Expected argument of type str,'
                            'but got %s' % type(method).__name__)
        self.method = str(method)

    def get_interface_identifier(self):
        """
        Returns the interface identifier of the method

        :rtype: :class:`InterfaceIdentifier`
        :return: InterfaceIdentifier of this method
        """
        return self.iface

    def get_name(self):
        """
        Returns the string identifier of the method

        :rtype: :class:`str`
        :return: String identifier of the method
        """
        return self.method

    def __eq__(self, other):
        return (isinstance(other, MethodIdentifier)
                and self.iface == other.iface
                and self.method == other.method)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'MethodIdentifier(%s, %s)' % (repr(self.iface),
                                             repr(self.method))

    def __hash__(self):
        return str(self).__hash__()


class ProviderDefinition(object):
    """
    The ProviderDefinition class contains details information about a
    vAPI provider
    """
    def __init__(self, name):
        """
        Initialize the ProviderDefinition

        :type  name: :class:`str`
        :param name: Name of the provider
        """
        self._name = name

    def get_identifier(self):
        """
        Returns the provider identifier.

        :rtype: :class:`str`
        :return: Provider identifier
        """
        return self._name

    def __eq__(self, other):
        return (isinstance(other, ProviderDefinition)
                and self._name == other.get_identifier())

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'ProviderDefinition(%s)' % repr(self._name)

    def __hash__(self):
        return str(self).__hash__()


class InterfaceDefinition(object):
    """
    The InterfaceDefinition class contains detailed information about a
    vAPI interface. This should contain all the information required
    to address an interface in the vAPI runtime.
    """
    def __init__(self, id_, method_ids):
        """
        Initialize the InterfaceDefinition

        :type  id_: :class:`InterfaceIdentifier`
        :param id_: InterfaceIdentifier of this interface
        :type  method_ids: :class:`list` of :class:`MethodIdentifier`
        :param method_ids: List of method identifiers of the methods exposed by
                           this interface
        """
        self.id_ = id_
        self.method_ids = method_ids

    def get_identifier(self):
        """
        Returns the interface identifier

        :rtype: :class:`InterfaceIdentifier`
        :return: Returns the interface identifer of this interface
        """
        return self.id_

    def get_method_identifiers(self):
        """
        Returns the list of method identifiers of the methods exposed by this
        interface. Each method identifier is unique within an interface. The
        method identifiers returned are unordered

        :rtype: :class:`list` of :class:`MethodIdentifier`
        :return: List of method identifiers of the methods exposed by this
                 interface
        """
        return self.method_ids

    def __eq__(self, other):
        if not isinstance(other, InterfaceDefinition):
            return False

        if self.id_ != other.id_:
            return False

        # compare the unordered list of method ids
        method_names = sorted([method_id.get_name()
                              for method_id in self.method_ids])
        other_method_names = sorted([method_id.get_name()
                                    for method_id in other.method_ids])
        if method_names != other_method_names:
            return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return str(self).__hash__()

    def __repr__(self):
        repr_args = (repr(self.id_), repr(self.method_ids))
        return 'InterfaceDefinition(id_=%s, method_ids=%s)' % repr_args


class MethodDefinition(object):
    """
    This class contains detailed information about a vAPI method. This should
    contain all the information required to address a method in the vAPI
    runtime.
    """
    def __init__(self, id_, input_, output, errors):
        """
        Initialize MethodDefinition

        :type  id_: :class:`MethodIdentifier`
        :param id_: MethodIdentifier of this method
        :type  input_: :class:`vmware.vapi.data.definition.StructDefinition`
        :param input_: Struct definition corresponding to the method's input
            parameters
        :type  output: :class:`vmware.vapi.data.definition.DataDefinition`
        :param output: Data definition of the method's output
        :type  errors: iterable of
            :class:`vmware.vapi.data.definition.ErrorDefinition`
        :param errors: Error definitions describing the errors that this method
                       can report
        """
        self.id_ = id_
        self.input_ = input_
        self.output = output
        self._errors = dict(((e.name, e) for e in errors))

    def get_identifier(self):
        """
        Returns the method identifier

        :rtype: :class:`MethodIdentifier`
        :return: MethodIdentifier of this method
        """
        return self.id_

    def get_input_definition(self):
        """
        Returns the struct definition corresponding to the method's input
        parameters. The field names in the struct definition are the parameter
        names and the field values correspond to the data definition of the
        respective fields.

        :rtype: :class:`vmware.vapi.data.definition.StructDefinition`
        :return: StructDefinition correspoding to the method's input
        """
        return self.input_

    def get_output_definition(self):
        """
        Returns the data definition of the method's output

        :rtype: :class:`vmware.vapi.data.definition.DataDefinition`
        :return: Data definition of the method's output
        """
        return self.output

    def get_error_definitions(self):
        """
        Returns a set of error definitions describing the errors that this
        method can report

        :rtype: :class:`set` of
            :class:`vmware.vapi.data.definition.ErrorDefinition`
        :return: Set of error definitions describing the errors that this
            method can report
        """
        return frozenset(six.itervalues(self._errors))

    def get_error_definition(self, error_name):
        """
        Returns the error definition with the specified name reported by this
        method or None if this method doesn't report an error with the specified
        name.

        :type  error_name: :class:`str`
        :param error_name: Name of the error definition to return
        :rtype: :class:`vmware.vapi.data.definition.ErrorDefinition`
        :return: Error definition with the specified name reported by this
                 method or None if this method doesn't report an error with the
                 specified name.
        """
        return self._errors.get(error_name)

    def __eq__(self, other):
        if not isinstance(other, MethodDefinition):
            return NotImplemented

        if len(self._errors) != len(other._errors):  # pylint: disable=W0212
            return False

        for error_name in six.iterkeys(self._errors):
            if self._errors[error_name] != other.get_error_definition(
                    error_name):
                return False

        return (self.id_ == other.id_
                and self.input_ == other.input_
                and self.output == other.output)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return str(self).__hash__()

    def __repr__(self):
        args = (repr(self.id_),
                repr(self.input_),
                repr(self.output),
                repr(self.get_error_definitions()))
        return \
            'MethodDefinition(id_=%s, input_=%s, output=%s, errors=%s)' % args


class MethodResult(object):
    """
    The MethodResult class contains the result of a method call.
    It contains either the output of the method invocation or
    an error reported by the method invocation. These are mutually
    exclusive.

    :type output: :class:`vmware.vapi.data.value.DataValue`
    :ivar output: Method output
    :type error: :class:`vmware.vapi.data.value.ErrorValue`
    :ivar error: Method error
    """
    def __init__(self, output=None, error=None):
        """
        Initialize MethodResult

        :type  output: :class:`vmware.vapi.data.value.DataValue`
        :param output: Method output
        :type  error: :class:`vmware.vapi.data.value.ErrorValue`
        :param error: Method error
        """
        self._output = output
        self._error = error

    @property
    def output(self):
        """
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: Method output
        """
        return self._output

    @property
    def error(self):
        """
        :rtype: :class:`vmware.vapi.data.value.ErrorValue`
        :return: Method error
        """
        return self._error

    def success(self):
        """
        Check if the method completed successfully.

        :rtype: :class:`bool`
        :return: False if the method reported an error, True otherwise
        """
        return (self.error is None)

    def __hash__(self):
        return str(self).__hash__()

    def __repr__(self):
        return 'MethodResult(output=%s, error=%s)' % (self._output, self._error)


class CustomDict(dict):
    """
    Interface for implementing Custom dict classes with additional constraints.

    Overriding __setitem__ as not enough for adding additional constraints on
    key/value pairs of dictionaries. We also have to override update and
    setdefault, so that even they use __setitem__.
    """
    # Same as dict setdefault, except this will call through our __setitem__
    def update(self, *args, **kwargs):
        for k, v in six.iteritems(dict(*args, **kwargs)):
            self[k] = v

    # Same as dict setdefault, except this will call through our __setitem__
    def setdefault(self, key, val=None):
        if key in self:
            return self[key]
        else:
            self[key] = val
            return val


class ApplicationContext(CustomDict):
    """
    Interface representing additional data associated with the request for
    method execution represented by this ExecutionContext.
    The additional data format is key-value pairs of String.

    This additional data is provided by the client initiating the
    execution, it is then transported as is over the wire and is
    available for the provider-side service implementations on the server.
    This extra data is completely opaque for the infrastructure, in other
    words it is a contract between the client and the service implementation
    only.
    """
    def __init__(self, *args, **kwargs):
        CustomDict.__init__(self)
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise TypeError('Type of key should be a string, but got %s' %
                            type(key).__name__)
        if not isinstance(value, six.string_types):
            raise TypeError('Type of value should be a string, but got %s' %
                            type(value).__name__)
        dict.__setitem__(self, key, value)

    def __repr__(self):
        return 'ApplicationContext(%s)' % dict.__repr__(self)


class SecurityContext(CustomDict):
    """
    Implementations of this interface will provide all needed data for
    authentication for the given invocation.
    """
    def __init__(self, *args, **kwargs):
        CustomDict.__init__(self)
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise TypeError('Type of key should be a string, but got %s' %
                            type(key).__name__)
        dict.__setitem__(self, key, value)

    def __repr__(self):
        return 'SecurityContext(<hidden>)'

    def __str__(self):
        return '<security-context>'


class RuntimeData(CustomDict):
    """
    Implementations of this interface will provide custom runtime data.
    """
    def __init__(self, *args, **kwargs):
        CustomDict.__init__(self)
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        if not isinstance(key, six.string_types):
            raise TypeError('Type of key should be a string, but got %s' %
                            type(key).__name__)
        dict.__setitem__(self, key, value)

    def __repr__(self):
        return 'RuntimeData(<hidden>)'

    def __str__(self):
        return '<runtime-data>'


class ExecutionContext(object):
    """
    This class provides out-of-band context information that is passed along
    with a method invocation
    """
    def __init__(self,
                 application_context=None,
                 security_context=None,
                 runtime_data=None):
        """
        Initialize Execution Context
        """
        if (application_context is not None
                and not isinstance(application_context, ApplicationContext)):
            raise TypeError('Application context should be of type '
                            'vmware.vapi.core.ApplicationContext')
        if application_context is None:
            application_context = ApplicationContext()

        if (security_context is not None
                and not isinstance(security_context, SecurityContext)):
            raise TypeError('Security context should be of type '
                            'vmware.vapi.core.SecurityContext')
        if security_context is None:
            security_context = SecurityContext()

        if (runtime_data is not None
                and not isinstance(runtime_data, RuntimeData)):
            raise TypeError('Runtime Data should be of type '
                            'vmware.vapi.core.RuntimeData')
        if runtime_data is None:
            runtime_data = RuntimeData()

        self.application_context = application_context
        self.security_context = security_context
        self.runtime_data = runtime_data

    def __hash__(self):
        return str(self).__hash__()

    def __repr__(self):
        app_ctx = 'application_context=%s' % repr(self.application_context)
        sec_ctx = 'security_context=%s' % repr(self.security_context)
        runtime_data = 'runtime_data=%s' % repr(self.runtime_data)
        return 'ExecutionContext(%s, %s, %s)' % (app_ctx, sec_ctx, runtime_data)
