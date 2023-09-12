from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine.url import make_url
from logging.config import fileConfig
from urllib.parse import quote

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from flask import current_app


def set_database_url(config):
    url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
    try:
        # In case of MySQL, add ``charset=utf8`` to the parameters (if no charset is set),
        # because this is what Flask-SQLAlchemy does
        if url.startswith("mysql"):
            parsed_url = make_url(url)
            parsed_url = parsed_url.update_query_dict({"charset": "utf8"})
            # We need to quote the password in case it contains special chars
            parsed_url = parsed_url.set(password=quote(parsed_url.password))
            url = str(parsed_url)
    except Exception as exx:
        print(u"Attempted to set charset=utf8 on connection, but failed: {}".format(exx))
    # set_main_option() requires escaped "%" signs in the string
    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))


set_database_url(config)
target_metadata = current_app.extensions['migrate'].db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # FIX for Postgres updates
    url = config.get_section(config.config_ini_section).get("sqlalchemy.url")
    driver = url.split(":")[0]

    if driver == "postgresql+psycopg2":
        engine = engine_from_config(
                    config.get_section(config.config_ini_section),
                    prefix='sqlalchemy.',
                    isolation_level="AUTOCOMMIT",
                    poolclass=pool.NullPool)
    else:
        engine = engine_from_config(
                    config.get_section(config.config_ini_section),
                    prefix='sqlalchemy.',
                    poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


if context.is_offline_mode():
    print("Running offline")
    run_migrations_offline()
else:
    print("Running online")
    run_migrations_online()
