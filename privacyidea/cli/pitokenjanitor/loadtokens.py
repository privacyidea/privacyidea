
from flask.cli import AppGroup
import click

from privacyidea.lib.token import import_token

loadtokens_cli = AppGroup("load", help="Loads token data from a PSKC file.")


@loadtokens_cli.command("load")
@click.option('--pskc',
              help='Import this PSKC file.')
@click.option('--preshared_key_hex',
              help='The AES encryption key.')
@click.option('--validate_mac', default='check_fail_hard',
              help="How the file should be validated.\n"
                   "'no_check' : Every token is parsed, ignoring HMAC\n"
                   "'check_fail_soft' : Skip tokens with invalid HMAC\n"
                   "'check_fail_hard' : Only import tokens if all HMAC are valid.")
def loadtokens(pskc, preshared_key_hex, validate_mac):
    """
    Loads token data from a PSKC file.
    """
    from privacyidea.lib.importotp import parsePSKCdata

    with open(pskc, 'r') as pskcfile:
        file_contents = pskcfile.read()

    tokens, not_parsed_tokens = parsePSKCdata(file_contents,
                                              preshared_key_hex=preshared_key_hex,
                                              validate_mac=validate_mac)
    success = 0
    failed = 0
    failed_tokens = []
    for serial in tokens:
        try:
            print("Importing token {0!s}".format(serial))
            import_token(serial, tokens[serial])
            success = success + 1
        except Exception as e:
            failed = failed + 1
            failed_tokens.append(serial)
            print("--- Failed to import token. {0!s}".format(e))

    if not_parsed_tokens:
        print("The following tokens were not read from the PSKC file"
              " because they could not be validated: {0!s}".format(not_parsed_tokens))
    print("Successfully imported {0!s} tokens.".format(success))
    print("Failed to import {0!s} tokens: {1!s}".format(failed, failed_tokens))