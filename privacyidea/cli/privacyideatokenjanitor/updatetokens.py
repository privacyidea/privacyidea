
import click
from flask.cli import AppGroup
from yaml import safe_load as yaml_safe_load
from privacyidea.lib.token import get_tokens
import sys

updatetokens_cli = AppGroup("update", help="This can update existing tokens in the privacyIDEA system.")


@updatetokens_cli.command("update")
@click.option('--yaml',
              help='Specify the YAML file with the previously exported tokens.')
def updatetokens(yaml):
    """
    This can update existing tokens in the privacyIDEA system. You can specify a yaml file with the tokendata.
    Can be used to reencrypt data, when changing the encryption key.
    """
    print("Loading YAML data. This may take a while.")
    token_list = yaml_safe_load(open(yaml, 'r').read())
    for tok in token_list:
        del (tok["owner"])
        tok_objects = get_tokens(serial=tok.get("serial"))
        if len(tok_objects) == 0:
            sys.stderr.write("\nCan not find token {0!s}. Not updating.\n".format(tok.get("serial")))
        else:
            print("Updating token {0!s}.".format(tok.get("serial")))
            try:
                tok_objects[0].update(tok)
            except Exception as e:
                sys.stderr.write("\nFailed to update token {0!s}.".format(tok.get("serial")))
