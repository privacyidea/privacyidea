# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.

import base64
import os
import pathlib
import sys
import click
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from flask.cli import AppGroup
from flask import current_app
from flask_migrate import stamp as fm_stamp
import gnupg
try:
    from importlib import metadata
except ImportError:  # Python 3.7
    import importlib_metadata as metadata

from privacyidea.models import db
from privacyidea.lib.security.default import DefaultSecurityModule

setup_cli = AppGroup("setup", short_help="privacyIDEA server setup",
                     help="Commands to setup the privacyIDEA server for production")


@setup_cli.command("encrypt_enckey", short_help="Additionally encrypt the encryption key")
@click.argument("encfile", type=click.File("rb"))
@click.option("-o", "--outfile", type=click.File("w"), default=sys.stdout,
              help="The file to which the encrypted encryption key will be "
                   "written to (default: stdout)")
@click.password_option(help="The password to encrypt the encryption key. "
                            "If this option is not given the user will be "
                            "prompted for the password.")
def encrypt_enckey(encfile, outfile, password):
    """
    You will be asked for a password and the given encryption key in the specified
    file will be encrypted with an AES key derived from your password.

    The encryption key in the file is a 96 bit binary key.

    The password based encrypted encryption key is a hex combination of an IV
    and the encrypted data.

    The result can be piped to a new enckey file.
    """
    # TODO we just print out a string here and assume, the user pipes it into a file.
    #      Maybe we should write the file here so we know what is in there
    # TODO: get the name/path of the encfile from the pi.cfg
    enckey = encfile.read()
    res = DefaultSecurityModule.password_encrypt(enckey, password)
    outfile.write(res)
    outfile.write('\n')


@setup_cli.command("create_enckey")
@click.option("-e", "--enckey_b64", type=str,
              help="base64 encoded plain text key")
@click.pass_context
def create_enckey(ctx, enckey_b64):
    """
    Create a key for encrypting the sensitive database entries.

    If the key of the given configuration does not yet exist, it will be created.
    Optionally a base64 encoded key can be passed with the "--enckey_b64" option.

    Warning: passing the encryption key as a parameter is considered harmful!
    """
    enc_file = pathlib.Path(current_app.config.get("PI_ENCFILE"))
    if enc_file.is_file():
        click.secho(f"The file \n\t{enc_file}\nalready exist. We do not overwrite it!",
                    fg="yellow")
        ctx.exit(1)
    with open(enc_file, "wb") as f:
        if enckey_b64 is None:
            f.write(DefaultSecurityModule.random(96))
        else:
            click.secho("Warning: Passing enckey via cli input is considered harmful.",
                        fg="yellow")
            bin_enckey = base64.b64decode(enckey_b64)
            if len(bin_enckey) != 96:
                click.secho("Error: enckey must be 96 bytes length", fg="red")
                ctx.exit(1)
            f.write(bin_enckey)
    click.secho(f"Encryption key written to {enc_file}", fg="green")
    enc_file.chmod(0o400)
    click.secho(f"The file permission of {enc_file} was set to 400!", fg="yellow")
    click.secho("Please ensure, that it is owned by the right user.", fg="yellow")


@setup_cli.command("create_pgp_keys")
@click.option("-f", "--force", is_flag=True,
              help="Overwrite existing PGP keys")
@click.option("-k", "--keysize", type=int, default=2048, show_default=True,
              help="Size of the generated PGP keys (in bits)")
@click.pass_context
def create_pgp_keys(ctx, keysize, force):
    """
    Generate PGP keys to allow encrypted token import.
    """
    # TODO: change owner and permission of gpg directory
    gpg_home = pathlib.Path(current_app.config.get("PI_GNUPG_HOME", "/etc/privacyidea/gpg"))
    if not gpg_home.exists():
        try:
            gpg_home.mkdir(parents=True)
        except IOError as e:
            click.secho(f"Could not create PGP directory {gpg_home}: {e}", fg="red")
            ctx.exit(1)
    gpg = gnupg.GPG(gnupghome=gpg_home)
    keys = gpg.list_keys(True)
    if len(keys) and not force:
        click.secho("There are already private keys. If you want to generate a "
                    "new private key, use the parameter --force.", fg="yellow")
        click.echo(f"uids: {keys[0]['uids']}\t fingerprint: {keys[0]['fingerprint']}")
        ctx.exit(1)
    else:
        click.secho("Overwriting existing PGP keys!", fg="yellow")
    input_data = gpg.gen_key_input(key_type="RSA", key_length=keysize,
                                   name_real="privacyIDEA Server",
                                   name_comment="Import")
    inputs = input_data.split("\n")
    if inputs[-2] == "%commit":
        del (inputs[-1])
        del (inputs[-1])
        inputs.append("%no-protection")
        inputs.append("%commit")
        inputs.append("")
        input_data = "\n".join(inputs)
    gpg.gen_key(input_data)


@setup_cli.command("create_audit_keys")
@click.option("-k", "--keysize", type=int, default=2048, show_default=True,
              help="Create keys with the given size in bits")
@click.pass_context
def create_audit_keys(ctx, keysize):
    """
    Create the RSA signing keys for the audit log.

    You may specify a different key size.
    The default key size is 2048 bit.
    """
    priv_key = pathlib.Path(current_app.config.get("PI_AUDIT_KEY_PRIVATE"))
    if priv_key.is_file():
        click.secho(f"The file \n\t{priv_key}\nalready exist. We do not overwrite it!",
                    fg="yellow")
        ctx.exit(1)
    new_key = rsa.generate_private_key(public_exponent=65537,
                                       key_size=keysize,
                                       backend=default_backend())
    priv_pem = new_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption())
    with open(priv_key, "wb") as f:
        f.write(priv_pem)

    pub_key = pathlib.Path(current_app.config.get("PI_AUDIT_KEY_PUBLIC"))
    public_key = new_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(pub_key, "wb") as f:
        f.write(pub_pem)

    click.secho(f"Signing keys written to {priv_key} and {pub_key}", fg="green")
    priv_key.chmod(0o400)
    click.secho(f"The file permission of {priv_key} was set to 400!", fg="yellow")
    click.secho("Please ensure, that it is owned by the right user.", fg="yellow")


@setup_cli.command("create_tables")
@click.option("-n", "--no-stamp", is_flag=True, default=False,
              show_default=True, help='Do not stamp the database to a revision.')
@click.option("-s", "--stamp", is_flag=True, default=False, hidden=True)
def create_tables(no_stamp, stamp):
    """
    Initially create the tables in the database. The database must exist
    (an SQLite database will be created).
    """
    click.echo(f"Using connect string {db}")
    if stamp:
        click.secho("The parameter \"--stamp\" is deprecated, the database "
                    "will be stamped by default. Use parameter \"--no-stamp\" "
                    "to prevent this.", fg="yellow")
    db.create_all()
    if not no_stamp:
        # get the path to the migration directory from the distribution
        p = [x.locate() for x in metadata.files('privacyidea') if
             'migrations/env.py' in str(x)]
        migration_dir = os.path.dirname(os.path.abspath(p[0]))
        fm_stamp(directory=migration_dir)
    db.session.commit()


@setup_cli.command("drop_tables")
@click.option("-d", "--dropit", type=str,
              help="If You are sure to drop the tables, pass the parameter \"yes\"")
def drop_tables(dropit):
    """
    This drops all the privacyIDEA database tables.
    Use with caution! All data will be lost!

    For safety reason you need to pass "--dropit==yes",
    otherwise the command will not drop anything.
    """
    if dropit == "yes":
        click.echo("Dropping all database tables!")
        db.drop_all()
        table_name = "alembic_version"
        db.reflect()
        table = db.metadata.tables.get(table_name, None)
        if table is not None:
            db.metadata.drop_all(bind=db.engine,
                                 tables=[table],
                                 checkfirst=True)
    else:
        click.echo("Not dropping anything!")
