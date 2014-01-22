# vim: tabstop=4 shiftwidth=4 softtabstop=4
"""
Auth plugin for heat when running standalone (if not, you need a client-side
plugin) to send HP-IDM-compliant access/secret key authentication.

This replaces the password auth mechanism packaged with heat.
To install, in api-paste.ini (/etc/heat/api-paste.ini), remove authpassword
from the `heat-api-standalone` pipeline and replace with `authsecretkey`. At
the bottom, add:

    [filter:authsecretkey]
    paste.filter_factory = heat_secretkey.auth_plugin:filter_factory

You can supply an API access and secret in os-username and os-password.
"""

from keystoneclient.v2_0 import client as keystone_client
from keystoneclient import exceptions as keystone_exceptions
from oslo.config import cfg

from heat.common.auth_password import KeystonePasswordAuthProtocol

import logging

LOG = logging.getLogger(__name__)

class SecretKeyClient(keystone_client.Client):
    """
    Subclass v2 keystone client to replace the JSON body it normally sends
    with the HP-IDM api access/secret key combination. Falls back on
    username/password on a 401 error (so both should work).
    """
    def _base_authN(self, auth_url, username=None, password=None,
                    tenant_name=None, tenant_id=None, trust_id=None,
                    token=None):
        """
        Changes the client code's JSON payload to send 'apiAccessKeyCredentials'
        instead of passwordCredentials. If authentication fails with 401, will
        fall back to username password. If the server doesn't recognize the
        payload it will return a 400 Bad Request; you should not be using this
        authentication protocol.
        """
        headers = {}
        if auth_url is None:
            raise ValueError("Cannot authenticate without a valid auth_url")
        url = auth_url + "/tokens"
        if token:
            headers['X-Auth-Token'] = token
            params = {"auth": {"token": {"id": token}}}
        elif username and password:
            LOG.debug("Treating username/password as access/secret key")
            params = {
                "auth": {
                    "apiAccessKeyCredentials": {
                        "accessKey": username,
                        "secretKey": password
                    }
                }
            }
        else:
            raise ValueError('A username and password or token is required.')
        if tenant_id:
            params['auth']['tenantId'] = tenant_id
        elif tenant_name:
            params['auth']['tenantName'] = tenant_name
        if trust_id:
            params['auth']['trust_id'] = trust_id

        try:
            resp, body = self.request(url, 'POST', body=params, headers=headers)
        except keystone_exceptions.Unauthorized:
            if not token:
                LOG.info(
                    "Access key auth failed; falling back to username/pass")
                # Maybe it's actually a username and password; try that instead
                return super(SecretKeyClient, self)._base_authN(
                        auth_url, username, password,
                        tenant_name, tenant_id, trust_id,
                        token)
        return resp, body


class KeystoneSecretKeyAuthProtocol(KeystonePasswordAuthProtocol):
    """
    Authentication protocol for heat-standalone using the modified keystone
    above. Note that this still uses the X_AUTH_USER and _KEY headers for now,
    since currently there's no pluggable authentication headers available.

    If you use this on an auth server that doesn't support HP-IDM you will
    likely get a 400 Bad Request response for authentication requests.
    """
    def __call__(self, env, start_response):
        """Authenticate incoming request."""
        username = env.get('HTTP_X_AUTH_USER')
        password = env.get('HTTP_X_AUTH_KEY')
        # Determine tenant id from path.
        tenant = env.get('PATH_INFO').split('/')[1]
        auth_url = self.auth_url
        if cfg.CONF.auth_password.multi_cloud:
            auth_url = env.get('HTTP_X_AUTH_URL')
            error = self._validate_auth_url(env, start_response, auth_url)
            if error:
                return error
        if not tenant:
            return self._reject_request(env, start_response, auth_url)
        try:
            # Construct a modified keystone client and try to authorize
            client = SecretKeyClient(
                username=username, password=password, tenant_id=tenant,
                auth_url=auth_url)
        except (keystone_exceptions.Unauthorized,
                keystone_exceptions.Forbidden,
                keystone_exceptions.NotFound,
                keystone_exceptions.AuthorizationFailure):
            return self._reject_request(env, start_response, auth_url)
        env['keystone.token_info'] = client.auth_ref
        env.update(self._build_user_headers(client.auth_ref, auth_url))
        return self.app(env, start_response)

    def _build_user_headers(self, token_info, auth_url):
        """Adds `AUTH_SECRET_KEY` header"""
        rval = super(KeystoneSecretKeyAuthProtocol, self).\
                _build_user_headers(token_info, auth_url)
        rval['HTTP_X_AUTH_SECRET_KEY'] = 'Yes'
        return rval


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return KeystoneSecretKeyAuthProtocol(app, conf)
    return auth_filter

