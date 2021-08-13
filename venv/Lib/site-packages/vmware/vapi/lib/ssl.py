"""
SSL Context factories
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from OpenSSL import SSL, crypto

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class ClientContextFactory(object):
    """
    Context factory base class. This class should be used to set the
    SSL options
    """
    def get_context(self):
        """
        Returns the SSL context
        """
        raise NotImplementedError


class DefaultClientContextFactory(ClientContextFactory):
    """
    Default SSL context class. This chooses some default options for SSL context.
    Clients can retrieve the context.

    To modify the context and set some options directly. Create a class like below
    and set the options. Pass this to the get_connector function

    class CustomClientContextFactory(DefaultClientContextFactory):
        def get_context(self):
            ctx = DefaultClientContextFactory.get_context(self)
            # modify ctx
            return ctx
    """
    def __init__(self, certificate=None, private_key=None, ca_certs=None,
                 ca_certs_dir=None):
        """
        Initialize DefaultClientContextFactory

        :type  certificate: :class:`str`
        :param certificate: File path of the certificate
        :type  private_key: :class:`str`
        :param private_key: File path of the private key
        :type  ca_certs: :class:`str`
        :param ca_certs: File path of ca certificates
        :type  ca_certs_dir: :class:`str`
        :param ca_certs_dir: Directory prepared using the c_rehash tool
            included with OpenSSL
        """

        def callback_fn(conn, cert, errno, depth, result):  # pylint: disable=W0613
            """
            Callback to handle the cert validation

            :type  conn: :class:`OpenSSL.SSL.Connection`
            :param conn: OpenSSL connection that triggered the verification
            :type  cert: :class:`OpenSSL.crypto.X509`
            :param cert: Certificate that is being validated
            :type  errno: :class:`int`
            :param errno: An integer containing the error number (0 in case no
                error) of the error detected. Error descriptions here:
                    http://www.openssl.org/docs/apps/verify.html
            :type  depth: :class:`int`
            :param depth: An integer indicating the depth of the certificate
                being validated. If it is 0 then it means it is the given
                certificate is the one being validated, in other case is one
                of the chain of certificates
            :type  result: :class:`int`
            :param result: An integer that indicates whether the validation of
                the certificate currently being validated (the one in the
                second argument) passed or not the validation. A value of 1 is
                a successful validation and 0 an unsuccessful one.
            :rtype: :class:`bool`
            :return: True if the verification passes, False otherwise
            """
            logger.debug(
                'Verifying SSL certificate at depth %s, subject %s, issuer %s',
                depth, repr(cert.get_subject()), repr(cert.get_issuer()))

            if errno:
                try:
                    fn = crypto.X509_verify_cert_error_string
                    errmsg = ':%s' % fn(errno)
                except AttributeError:
                    errmsg = ''
                logger.error('verify error %s: %s', errno, errmsg)
                return False
            return True

        # Connect to server supporting TLSv1.0, TLSv1.1, TLSv1.2
        self._context = SSL.Context(SSL.SSLv23_METHOD)
        # Disable the insecure SSLv2 and SSLv3 connections
        self._context.set_options(SSL.OP_NO_SSLv2)
        self._context.set_options(SSL.OP_NO_SSLv3)
        self._context.set_verify(SSL.VERIFY_PEER, callback_fn)

        if certificate:
            self._context.use_certificate_file(certificate)
        if private_key:
            self._context.use_privatekey_file(private_key)
        if ca_certs or ca_certs_dir:
            try:
                self._context.load_verify_locations(
                    ca_certs.encode('utf-8'), ca_certs_dir)
            except TypeError:
                self._context.load_verify_locations(
                    ca_certs, ca_certs_dir)

    def get_context(self):
        """
        Returns the SSL context

        :rtype: :class:`OpenSSL.SSL.Context`
        :return: SSL context
        """
        return self._context


class UnverifiedClientContextFactory(DefaultClientContextFactory):
    """
    Unverified SSL context class. This class retrieves an unverified SSL Context
    with other options from the DefaultClientContext
    """
    def __init__(self):
        DefaultClientContextFactory.__init__(self)
        self._context.set_verify(SSL.VERIFY_NONE, lambda *x: True)
