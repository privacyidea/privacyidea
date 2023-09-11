"""v3.9: Create sequences needed for SQLAlchemy 1.4

E.g. mariadb now needs sequences.

Revision ID: 5cb310101a1f
Revises: 4a0aec37e7cf
Create Date: 2023-09-08 15:59:01.374626

"""

# revision identifiers, used by Alembic.
revision = '5cb310101a1f'
down_revision = '4a0aec37e7cf'

from alembic import op, context
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
from privacyidea.models import (Audit, AuthCache, CAConnector, CAConnectorConfig, Challenge,
                                ClientApplication, CustomUserAttribute, EventCounter, EventHandler, EventHandlerOption,
                                EventHandlerCondition, MachineResolver, MachineResolverConfig, MachineToken,
                                MachineTokenOptions, MonitoringStats, PasswordReset, PeriodicTask, PeriodicTaskOption,
                                PeriodicTaskLastRun, Policy, PolicyCondition, PrivacyIDEAServer, RADIUSServer, Realm,
                                Resolver, ResolverConfig, ResolverRealm, Serviceid, SMSGateway, SMSGatewayOption,
                                SMTPServer, Subscription, Token, TokenRealm, TokenTokengroup, Tokengroup, TokenInfo,
                                TokenOwner, UserCache)


Session = sessionmaker()

# Not clear how to get a non-default sequence name, so we define them here:
TABLES = [(Audit, "audit_seq"), (AuthCache, None), (CAConnector, None), (CAConnectorConfig, "caconfig_seq"),
          (Challenge, None), (ClientApplication, "clientapp_seq"), (CustomUserAttribute, None), (EventCounter, None),
          (EventHandler, None), (EventHandlerOption, "eventhandleropt_seq"), (EventHandlerCondition, "eventhandlercond_seq"),
          (MachineResolver, None), (MachineResolverConfig, "machineresolverconf_seq"), (MachineToken, None),
          (MachineTokenOptions, "machtokenopt_seq"),
          (MonitoringStats, None), (PasswordReset, "pwreset_seq"), (PeriodicTask, None), (PeriodicTaskOption, "periodictaskopt_seq"),
          (PeriodicTaskLastRun, None), (Policy, None), (PolicyCondition, None),
          (PrivacyIDEAServer, None), (RADIUSServer, None), (Realm, None), (Resolver, None), (ResolverConfig, "resolverconf_seq"),
          (ResolverRealm, None), (Serviceid, None), (SMSGateway, None), (SMSGatewayOption, "smsgwoption_seq"), (SMTPServer, None),
          (Subscription, None), (Token, None), (TokenRealm, None), (TokenTokengroup, None), (Tokengroup, None),
          (TokenInfo, None), (TokenOwner, None), (UserCache, None)]


def upgrade():

    migration_context = context.get_context()
    if migration_context.dialect.supports_sequences:
        bind = op.get_bind()
        # We only need a read session, so we do not need a commit
        session = Session(bind=bind)

        for Tab, sequence_name in TABLES:
            try:
                # Create the sequence with the correct next_id!
                # We get a tuple or (None, ) or (21, ).
                current_id = session.query(func.max(Tab.id)).one()[0] or 1
                # In case we have non-synced redundancy, we skip some values
                next_id = current_id + 10
                print("CurrentID in Table {0!s}: {1!s}".format(Tab.__tablename__, current_id))
                # Use the given sequecne name or use the default one.
                sequence_name = sequence_name or '{0!s}_seq'.format(Tab.__tablename__)
                seq = Sequence(sequence_name, start=next_id)
                print(" +++ Creating Sequence: {0!s}".format(sequence_name))
                op.execute(CreateSequence(seq, if_not_exists=True))
            except Exception as exx:
                print(exx)


def downgrade():

    migration_context = context.get_context()
    if migration_context.dialect.supports_sequences:

        for Tab, sequence_name in TABLES:
            try:
                sequence_name = sequence_name or '{0!s}_seq'.format(Tab.__tablename__)
                seq = Sequence(sequence_name)
                op.execute(DropSequence(seq, if_exists=True))
            except Exception as exx:
                print(exx)
