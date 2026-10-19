from unittest import mock

from privacyidea.lib.resolvers.EntraIDResolver import (
    CLIENT_CREDENTIAL_TYPE, CLIENT_ID, CLIENT_SECRET, TENANT, ClientCredentialType, EntraIDResolver,
)


def test_msal_uses_resolver_timeout():
    config = {
        CLIENT_ID: "1234",
        CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
        CLIENT_SECRET: "secret",
        TENANT: "organization",
        "timeout": 12,
    }
    with mock.patch(
        "privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication"
    ) as application:
        EntraIDResolver().loadConfig(config)

    assert application.call_args.kwargs["timeout"] == 12
