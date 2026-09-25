# 2023-11-03 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#            Migrate to click
# 2020-11-11 Timo Sturm <timo.sturm@netknights.it>
#            Select how to validate PSKC imports
# 2018-02-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Allow to import PSKC file
# 2017-11-21 Cornelius Kölbel <corenlius.koelbel@netknights.it>
#            export to CSV including usernames
# 2017-10-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add token export (HOTP and TOTP) to PSKC
# 2017-05-02 Friedrich Weber <friedrich.weber@netknights.it>
#            Improve token matching
# 2017-04-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# Copyright (c) 2017, Cornelius Kölbel
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE

import click
from flask.cli import AppGroup
from yaml import safe_load as yaml_safe_load
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokenclass import TokenClass
import sys


updatetokens_cli = AppGroup("update")


def _keep_token_state(token_object: TokenClass, token_data: dict, count: int, failcount: int,
                      tokenkind: str | None) -> None:
    """
    Storing the OTP key of a token resets its OTP counter and its fail counter and marks it as a software token. The
    OTP key of an export entry is the key the token already has, so put the rest back: the fail counter and the token
    kind keep their values, and the OTP counter keeps its value or takes the counter of the export, if that is higher.
    A lower OTP counter would make OTP values the token has already used valid again.

    :param token_object: the updated token
    :param token_data: the entry of the token in the YAML export
    :param count: the OTP counter of the token before the update
    :param failcount: the fail counter of the token before the update
    :param tokenkind: the token kind of the token before the update
    """
    token_object.token.count = max(count or 0, int(token_data.get("counter") or 0))
    token_object.token.failcount = failcount
    if tokenkind:
        token_object.write_tokeninfo("tokenkind", tokenkind)
    token_object.token.save()


@updatetokens_cli.command("update")
@click.argument('yaml', type=click.File())
def updatetokens(yaml):
    """
    Update existing tokens in the privacyIDEA system. You must specify a YAML
    file with the tokendata.
    Can be used to reencrypt data, when changing the encryption key.
    """
    click.echo("Loading YAML data. This may take a while.")
    token_list = yaml_safe_load(yaml.read())
    for tok in token_list:
        del (tok["owner"])
        serial = tok.get("serial")
        tok_objects = get_tokens(serial=serial)
        if len(tok_objects) == 0:
            sys.stderr.write(f"\nCan not find token {serial}. Not updating.\n")
        else:
            click.echo(f"Updating token {serial}.")
            token_object = tok_objects[0]
            count = token_object.token.count
            failcount = token_object.token.failcount
            tokenkind = token_object.get_tokeninfo("tokenkind")
            try:
                token_object.update(tok)
                _keep_token_state(token_object, tok, count, failcount, tokenkind)
            except Exception as e:
                click.echo(f"\nFailed to update token {serial} ({e}).", err=True)
