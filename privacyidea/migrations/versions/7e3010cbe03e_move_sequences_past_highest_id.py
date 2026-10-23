"""v3.14.1: Move every id sequence past the highest id of its table

privacyIDEA takes the id of a new row from the sequence of its table. A row that got its id somewhere else can be
ahead of the sequence: from AUTO_INCREMENT on MariaDB databases created before 3.9, from a data migration that inserted
rows without an id, or from an insert by hand. The sequence then hands out ids that already exist, and every row
privacyIDEA writes into that table fails with a duplicate primary key until the sequence has passed them.

The migration moves every sequence that is behind to the id after the highest one of its table. A sequence that is
already further ahead stays where it is. MySQL has no sequences and is not changed. The downgrade leaves the
sequences where they are.

Revision ID: 7e3010cbe03e
Revises: 4b810261d282
Create Date: 2026-10-23 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

from privacyidea.models.db import restart_sequence_past_max

revision = '7e3010cbe03e'
down_revision = '4b810261d282'
branch_labels = None
depends_on = None

# The tables whose id privacyIDEA takes from a sequence, with that sequence
TABLE_SEQUENCES = {
    'authcache': 'authcache_seq',
    'caconnector': 'caconnector_seq',
    'caconnectorconfig': 'caconfig_seq',
    'challenge': 'challenge_seq',
    'clientapplication': 'clientapp_seq',
    'customuserattribute': 'customuserattribute_seq',
    'description': 'description_seq',
    'eventcounter': 'eventcounter_seq',
    'eventhandler': 'eventhandler_seq',
    'eventhandlercondition': 'eventhandlercond_seq',
    'eventhandleroption': 'eventhandleropt_seq',
    'internaluserattribute': 'internaluserattribute_seq',
    'machineresolver': 'machineresolver_seq',
    'machineresolverconfig': 'machineresolverconf_seq',
    'machinetoken': 'machinetoken_seq',
    'machinetokenoptions': 'machtokenopt_seq',
    'metric_aggregate': 'metric_aggregate_seq',
    'monitoringstats': 'monitoringstats_seq',
    'passwordreset': 'pwreset_seq',
    'periodictask': 'periodictask_seq',
    'periodictasklastrun': 'periodictasklastrun_seq',
    'periodictaskoption': 'periodictaskopt_seq',
    'pidea_audit': 'audit_seq',
    'policy': 'policy_seq',
    'policycondition': 'policycondition_seq',
    'privacyideaserver': 'privacyideaserver_seq',
    'radiusserver': 'radiusserver_seq',
    'realm': 'realm_seq',
    'resolver': 'resolver_seq',
    'resolverconfig': 'resolverconf_seq',
    'resolverrealm': 'resolverrealm_seq',
    'serviceid': 'serviceid_seq',
    'smsgateway': 'smsgateway_seq',
    'smsgatewayoption': 'smsgwoption_seq',
    'smtpserver': 'smtpserver_seq',
    'subscription': 'subscription_seq',
    'token': 'token_seq',
    'tokencredentialidhash': 'tokencredentialidhash_seq',
    'tokengroup': 'tokengroup_seq',
    'tokeninfo': 'tokeninfo_seq',
    'tokenowner': 'tokenowner_seq',
    'tokenrealm': 'tokenrealm_seq',
    'tokentokengroup': 'tokentokengroup_seq',
    'usercache': 'usercache_seq',
    'usersetting': 'usersetting_seq',
}


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        return
    inspector = sa.inspect(bind)
    tables = {name.lower() for name in inspector.get_table_names()}
    sequences = {name.lower() for name in inspector.get_sequence_names()}
    for table, sequence in TABLE_SEQUENCES.items():
        if table in tables and sequence in sequences:
            restart_sequence_past_max(op, table, sequence, only_forward=True)


def downgrade() -> None:
    pass
