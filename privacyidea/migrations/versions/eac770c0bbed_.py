"""v3.10.2: Drop unique constraint on tokencontainerrealm

Revision ID: eac770c0bbed
Revises: 69e7817b9863
Create Date: 2024-10-30 11:21:28.721316

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'eac770c0bbed'
down_revision = '69e7817b9863'


def upgrade():
    migration_context = op.get_context()

    try:
        if migration_context.dialect.name in ['sqlite']:
            # SQLite allows constraint without a name, so we have to use a naming convention to be able to drop it
            naming_convention = {
                "ix": "ix_%(column_0_label)s",
                "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
                "ck": "ck_%(table_name)s_`%(constraint_name)s`",
                "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                "pk": "pk_%(table_name)s"
            }
            with op.batch_alter_table(
                    "tokencontainerrealm", naming_convention=naming_convention) as batch_op:
                batch_op.drop_constraint("uq_tokencontainerrealm_container_id_realm_id", type_="unique")

        else:
            # All other databases autogenerate a name for constraints, we just need to get this name to drop it
            bind = op.get_bind()
            insp = sa.inspect(bind.engine)
            uqs = insp.get_unique_constraints("tokencontainerrealm")
            columns = ["container_id", "realm_id"]
            for uq in uqs:
                if len(list(set(columns).intersection(uq['column_names']))) == 2:
                    op.drop_constraint(uq['name'], 'tokencontainerrealm', type_='unique')

    except (OperationalError, ProgrammingError) as exx:
        if "no such constraint" in str(exx.orig).lower():
            print("Unique constraint on tokencontainerrealm already removed.")
        else:
            print("Could not drop unique constraint on tokencontainerrealm.")
            print(exx)
    except ValueError as exx:
        if "no such constraint" in str(exx).lower():
            print("Unique constraint on tokencontainerrealm already removed.")
        else:
            print("Could not drop unique constraint on tokencontainerrealm.")
            print(exx)


def downgrade():
    pass
