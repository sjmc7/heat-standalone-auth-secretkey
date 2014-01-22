heat-standalone-auth-secretkey
==============================

This plugin allows a standalone heat server (i.e. one that authenticates as
the user, taking a username/password) to instead use an API access/secret key
as defined in the HP-IDM keystone extension (for examples of use, see
[HP Cloud Identity Management]
(http://docs.hpcloud.com/api/identity#authenticate-jumplink-span "HP identity").

This allows a client to specify an access/secret key as the `--os-username` and
`--os-password` parameters respectively (equivalent to the `X-Auth-User` and 
`X-Auth-Key` headers).

Installation
------------

With this library installed somewhere heat can find it:

- Open heat-api's `api-paste.ini` (typically `/etc/heat/api-paste.ini`)
- Locate `authpassword` in the `heat-standalone` pipeline (this plugin is
  what contacts keystone to ask for a token
- Replace it with `authsecretkey`
- At the bottom, add:

    [filter:authsecretkey]
    paste.filter_factory = heat_secretkey.auth_plugin:filter_factory

- Restart `heat-api`.

Usage
-----

    heat --os-no-client-auth \
       --os-username $OS_ACCESS_KEY_ID \
       --os-password $OS_SECRET_ACCESS_KEY \
       --heat-url http://localhost:8004/v1/$OS_TENANT_ID \
       stack-list

When you run heat in standalone with `--debug` you'll see a message to the
effect that the server's treating the username and password as access/secret
keys. If you instead pass a username and password, it will make a second request
to keystone.

If you're using heatclient as a library, pass your access and secret keys in
as the username/password arguments.
