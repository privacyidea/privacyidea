"""v3.10: Add column node_uuid to table resolverrealm

Revision ID: d0e7144947d0
Revises: e3a64b4ca634
Create Date: 2023-12-04 17:45:25.949596

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import DatabaseError

# revision identifiers, used by Alembic.
revision = 'd0e7144947d0'
down_revision = 'e3a64b4ca634'


def upgrade():
    migration_context = op.get_context()
    try:
        op.add_column('resolverrealm', sa.Column('node_uuid', sa.Unicode(length=36), nullable=True))
    except DatabaseError as e:
        if any(x in str(e.orig).lower() for x in ["already exists", "duplicate column name"]):
            print("Ok, column 'node_uuid' already exists.")
        else:
            raise
    except Exception as _e:
        print("Could not add column 'node_uuid' to table 'resolverrealm'")
        raise

    try:
        # unfortunately, MariaDB does not support removing a constraint with
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
        # for SQLAlchemy we need a batch operation
        with op.batch_alter_table('resolverrealm') as batch_op:
            batch_op.drop_constraint('rrix_2', type_='unique')
            # Oracle creates an additional index with the same name as the unique constraint.
            #  These indices have the same name and are not deleted automatically.
            if migration_context.dialect.name == 'oracle':
                batch_op.drop_index("rrix_2")

            if migration_context.dialect.name in ['mysql', 'mariadb']:
                # we have to re-create the foreign key constraints
                for ref_table in ['resolver', 'realm']:
                    batch_op.create_foreign_key(None, ref_table, [f'{ref_table}_id'], ['id'])
            # and re-create the unique constraint
            batch_op.create_unique_constraint('rrix_2', ['resolver_id', 'realm_id', 'node_uuid'])
    except DatabaseError as e:
        if "already exists" in str(e.orig).lower():
            print("Ok, constraint already exists.")
            print(e)
        else:
            raise
    except Exception as e:
        print(f"Could not change constraint 'rrix_2' on table 'resolverrealm': {e}")
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
        with op.batch_alter_table('resolverrealm') as batch_op:
            if migration_context.dialect.name == 'oracle':
                batch_op.drop_index("rrix_2")
            batch_op.drop_constraint('rrix_2', type_='unique')
            if migration_context.dialect.name in ['mysql', 'mariadb']:
                # we have to re-create the foreign key constraints
                for ref_table in ['resolver', 'realm']:
                    batch_op.create_foreign_key(None, ref_table, [f'{ref_table}_id'], ['id'])
            # and re-create the unique constraint
            batch_op.create_unique_constraint('rrix_2', ['resolver_id', 'realm_id'])
            batch_op.drop_column('node_uuid')
    except DatabaseError as e:
        if "already exists" in str(e.orig).lower():
            print("Ok, constraint already exists.")
            print(e)
        else:
            raise
    except Exception as _e:
        print("Could not change constraint 'rrix_2' on table 'resolverrealm'")
        raise
