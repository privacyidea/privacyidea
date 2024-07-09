"""v3.10: Add column node_uuid to table resolverrealm

Revision ID: d0e7144947d0
Revises: e3a64b4ca634
Create Date: 2023-12-04 17:45:25.949596

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'd0e7144947d0'
down_revision = 'e3a64b4ca634'


def upgrade():
    migration_context = op.get_context()
    try:
        op.add_column('resolverrealm', sa.Column('node_uuid', sa.Unicode(length=36), nullable=True))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, column 'node_uuid' already exists.")
        else:
            raise
    except Exception as _e:
        print("Could not add column 'node_uuid' to table 'resolverrealm'")
        raise

    try:
        # unfortunately MariaDB does not support removing a constraint with
        # foreign keys, so we have to remove the foreign keys before.
        if migration_context.dialect.name in ['mysql', 'mariadb']:
            bind = op.get_bind()
            insp = sa.inspect(bind.engine)
            fks = insp.get_foreign_keys('resolverrealm')
            for ref_table in ['resolver', 'realm']:
                fk_name = next((fk['name'] for fk in fks if fk['referred_table'] == ref_table), None)
                if fk_name:
                    op.drop_constraint(fk_name, 'resolverrealm', type_='foreignkey')
        # drop the unique constraint
        op.drop_constraint('rrix_2', 'resolverrealm', type_='unique')
        if migration_context.dialect.name in ['mysql', 'mariadb']:
            # we have to re-create the foreign key constraints
            for ref_table in ['resolver', 'realm']:
                op.create_foreign_key(None, 'resolverrealm', ref_table, [f'{ref_table}_id'], ['id'])
        # and re-create the unique constraint
        op.create_unique_constraint('rrix_2', 'resolverrealm', ['resolver_id', 'realm_id', 'node_uuid'])
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, constraint already exists.")
            print(exx)
        else:
            raise
    except Exception as _e:
        print("Could not change constraint 'rrix_2' on table 'resolverrealm'")
        raise


def downgrade():
    migration_context = op.get_context()
    try:
        # we need to drop the foreign key constraints first on MySQL/MariaDB
        if migration_context.dialect.name in ['mysql', 'mariadb']:
            bind = op.get_bind()
            insp = sa.inspect(bind.engine)
            fks = insp.get_foreign_keys('resolverrealm')
            for ref_table in ['resolver', 'realm']:
                fk_name = next((fk['name'] for fk in fks if fk['referred_table'] == ref_table), None)
                if fk_name:
                    op.drop_constraint(fk_name, 'resolverrealm', type_='foreignkey')
        # now we can drop the unique constraint
        op.drop_constraint('rrix_2', 'resolverrealm', type_='unique')
        if migration_context.dialect.name in ['mysql', 'mariadb']:
            # we have to re-create the foreign key constraints
            for ref_table in ['resolver', 'realm']:
                op.create_foreign_key(None, 'resolverrealm', ref_table, [f'{ref_table}_id'], ['id'])
        # and re-create the unique constraint
        op.create_unique_constraint('rrix_2', 'resolverrealm', ['resolver_id', 'realm_id'])
        op.drop_column('resolverrealm', 'node_uuid')
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, constraint already exists.")
            print(exx)
        else:
            raise
    except Exception as _e:
        print("Could not change constraint 'rrix_2' on table 'resolverrealm'")
        raise
