"""v3.6: move PUSH registration URL from Firebase Config to policies

Revision ID: fa07bd604a75
Revises: 3ba618f6b820
Create Date: 2021-05-18 23:29:59.273457

"""
from alembic import op
import sqlalchemy as sa

from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway, delete_smsgateway_option
from privacyidea.lib.tokens.pushtoken import GWTYPE, PUSH_ACTION
from privacyidea.lib.policy import PolicyClass, set_policy, SCOPE

# revision identifiers, used by Alembic.
revision = 'fa07bd604a75'
down_revision = '3ba618f6b820'


def upgrade():
    # Check if we even have Firebase-Gateways configured
    conn = op.get_bind()
    sms_gw = sa.table("smsgateway",
                      sa.column("id", sa.Integer),
                      sa.column("identifier", sa.Unicode(255)),
                      sa.column("description", sa.Unicode(1024)),
                      sa.column("providermodule", sa.Unicode(1024)))
    res = conn.execute(
        sms_gw.select().where(sms_gw.c.providermodule == GWTYPE)
    )
    # Somehow this does not work with Oracle. The query is correct, but the
    # result is empty even though the same query gives a result when issued directly.
    if not res.scalar():
        print(f"Rev. {revision}: No Firebase-Provider detected. Skipping migration.")
        return
    print(f"(Rev. {revision}) WARNING: Firebase-Provider detected. Check that the "
          f"migration was successful")

    # 1. Read the push_registration_url and ttl from the Firebase Config
    fb_gateways = get_smsgateway(gwtype=GWTYPE)
    # 2. Check which policy contains this Firebase Config
    P = PolicyClass()
    pols = P.list_policies(scope=SCOPE.ENROLL,
                           action="{0!s}".format(PUSH_ACTION.FIREBASE_CONFIG))

    # iterate through all enrollment policies
    for pol in pols:
        # Check for all firebase gateways if this policy needs to be modified
        for fbgw in fb_gateways:
            if pol.get("action").get(PUSH_ACTION.FIREBASE_CONFIG) == fbgw.identifier:
                print("Modifying policy {0!s}".format(pol.get("name")))
                # This is an enrollment policy that references this very firebase config
                # 3. Add the push_registration_url and ttl to this policy
                registration_url = fbgw.option_dict.get("registration URL")
                ttl = fbgw.option_dict.get("time to live")
                # We can leave most of the parameters None, since it will update the policy.
                # We still need to pass the original "active" and "check_all_resolvers" params
                # and we need to update the action
                action = pol.get("action")
                # Only add registration_url and ttl to the policy if these values actually exist,
                # to avoid deleting (setting an empty value) in the policy.
                if registration_url:
                    action[PUSH_ACTION.REGISTRATION_URL] = registration_url
                if ttl:
                    action[PUSH_ACTION.TTL] = ttl
                r = set_policy(name=pol.get("name"),
                               scope=SCOPE.ENROLL,
                               active=pol.get("active"),
                               check_all_resolvers=pol.get("check_all_resolvers"),
                               action=action)
                print("+- Updated policy {0!s}: {1!s}".format(pol.get("name"), r))
                # 4. Delete push_registration_url and ttl from the Firebase Config
                #    Note: If we had a firebase config, that would not be used in a policy,
                #    the url and ttl would not be deleted from the firebase config. But this
                #    does not matter. I like to keep it in this for-loop to avoid unknown side effects.
                print("Deleting URL and TTL from the Firebase Gateway config.")
                if registration_url:
                    delete_smsgateway_option(fbgw.id, "registration URL")
                if ttl:
                    delete_smsgateway_option(fbgw.id, "time to live")


def downgrade():
    # The only way is up.
    pass
