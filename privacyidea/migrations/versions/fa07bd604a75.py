"""v3.6: move PUSH registration URL from Firebase Config to policies

Revision ID: fa07bd604a75
Revises: 3ba618f6b820
Create Date: 2021-05-18 23:29:59.273457

"""
import sqlalchemy as sa
from alembic import op

from privacyidea.lib.tokens.pushtoken import GWTYPE, PUSH_ACTION

# revision identifiers, used by Alembic.
revision = 'fa07bd604a75'
down_revision = '3ba618f6b820'

# Raw table definitions to avoid using ORM models which reflect the current
# (head) schema instead of the schema at this point in the migration chain.
_sms_gw_table = sa.table("smsgateway",
                          sa.column("id", sa.Integer),
                          sa.column("identifier", sa.Unicode(255)),
                          sa.column("providermodule", sa.Unicode(1024)))

_sms_gw_option_table = sa.table("smsgatewayoption",
                                 sa.column("gateway_id", sa.Integer),
                                 sa.column("Key", sa.Unicode(255)),
                                 sa.column("Value", sa.UnicodeText()))

_policy_table = sa.table("policy",
                          sa.column("id", sa.Integer),
                          sa.column("name", sa.Unicode(64)),
                          sa.column("scope", sa.Unicode(32)),
                          sa.column("active", sa.Boolean),
                          sa.column("check_all_resolvers", sa.Boolean))

_policy_action_table = sa.table("policyaction",
                                 sa.column("id", sa.Integer),
                                 sa.column("policy_id", sa.Integer),
                                 sa.column("action", sa.Unicode(255)),
                                 sa.column("value", sa.Unicode(2000)))


def upgrade():
    conn = op.get_bind()

    # 1. Check if we even have Firebase-Gateways configured
    res = conn.execute(
        _sms_gw_table.select().where(_sms_gw_table.c.providermodule == GWTYPE)
    )
    fb_gw_rows = res.fetchall()
    if not fb_gw_rows:
        print(f"Rev. {revision}: No Firebase-Provider detected. Skipping migration.")
        return
    print(f"(Rev. {revision}) WARNING: Firebase-Provider detected. Check that the "
          f"migration was successful")

    # 2. For each Firebase gateway, load its options (registration URL and TTL)
    fb_gateways = {}
    for gw in fb_gw_rows:
        gw_id = gw[0]
        gw_identifier = gw[1]
        opts_res = conn.execute(
            _sms_gw_option_table.select().where(
                _sms_gw_option_table.c.gateway_id == gw_id
            )
        )
        options = {row[1]: row[2] for row in opts_res.fetchall()}
        fb_gateways[gw_identifier] = {"id": gw_id, "options": options}

    # 3. Find enrollment policies that reference a Firebase config
    enroll_policies_res = conn.execute(
        _policy_table.select().where(_policy_table.c.scope == "enroll")
    )
    enroll_policies = enroll_policies_res.fetchall()

    for pol in enroll_policies:
        pol_id = pol[0]
        pol_name = pol[1]

        # Load this policy's actions
        actions_res = conn.execute(
            _policy_action_table.select().where(
                _policy_action_table.c.policy_id == pol_id
            )
        )
        actions = {row[2]: row[3] for row in actions_res.fetchall()}
        firebase_config_value = actions.get(str(PUSH_ACTION.FIREBASE_CONFIG))

        if firebase_config_value and firebase_config_value in fb_gateways:
            fbgw = fb_gateways[firebase_config_value]
            registration_url = fbgw["options"].get("registration URL")
            ttl = fbgw["options"].get("time to live")

            print("Modifying policy {0!s}".format(pol_name))

            # Insert or update the registration URL action in this policy
            if registration_url:
                existing = conn.execute(
                    _policy_action_table.select().where(
                        sa.and_(
                            _policy_action_table.c.policy_id == pol_id,
                            _policy_action_table.c.action == str(PUSH_ACTION.REGISTRATION_URL)
                        )
                    )
                ).fetchone()
                if existing:
                    conn.execute(
                        _policy_action_table.update().where(
                            sa.and_(
                                _policy_action_table.c.policy_id == pol_id,
                                _policy_action_table.c.action == str(PUSH_ACTION.REGISTRATION_URL)
                            )
                        ).values(value=registration_url)
                    )
                else:
                    conn.execute(
                        _policy_action_table.insert().values(
                            policy_id=pol_id,
                            action=str(PUSH_ACTION.REGISTRATION_URL),
                            value=registration_url
                        )
                    )

            if ttl:
                existing = conn.execute(
                    _policy_action_table.select().where(
                        sa.and_(
                            _policy_action_table.c.policy_id == pol_id,
                            _policy_action_table.c.action == str(PUSH_ACTION.TTL)
                        )
                    )
                ).fetchone()
                if existing:
                    conn.execute(
                        _policy_action_table.update().where(
                            sa.and_(
                                _policy_action_table.c.policy_id == pol_id,
                                _policy_action_table.c.action == str(PUSH_ACTION.TTL)
                            )
                        ).values(value=ttl)
                    )
                else:
                    conn.execute(
                        _policy_action_table.insert().values(
                            policy_id=pol_id,
                            action=str(PUSH_ACTION.TTL),
                            value=ttl
                        )
                    )

            print("+- Updated policy {0!s}".format(pol_name))

            # 4. Delete registration URL and TTL from the Firebase Gateway options
            print("Deleting URL and TTL from the Firebase Gateway config.")
            gw_id = fbgw["id"]
            if registration_url:
                conn.execute(
                    _sms_gw_option_table.delete().where(
                        sa.and_(
                            _sms_gw_option_table.c.gateway_id == gw_id,
                            _sms_gw_option_table.c.Key == "registration URL"
                        )
                    )
                )
            if ttl:
                conn.execute(
                    _sms_gw_option_table.delete().where(
                        sa.and_(
                            _sms_gw_option_table.c.gateway_id == gw_id,
                            _sms_gw_option_table.c.Key == "time to live"
                        )
                    )
                )


def downgrade():
    # The only way is up.
    pass
