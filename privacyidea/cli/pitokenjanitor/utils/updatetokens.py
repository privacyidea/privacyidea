# SPDX-FileCopyrightText: (C) 2024 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# 2024-11-11 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#            New pi-token-janitor script
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
from flask.cli import with_appcontext
from yaml import safe_load as yaml_safe_load
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokenclass import TokenClass
import sys


def _update_token_keeping_state(token: TokenClass, token_data: dict) -> None:
    """
    Write the data of an entry of a YAML export to the token without resetting its counters.

    TokenClass.update() stores the OTP key as a new key and therefore resets the OTP counter and the fail counter,
    and marks the token as a software token. The OTP key of an export entry is the key the token already has, so OTP
    values that were already used must not become valid again: the OTP counter is kept, or raised to the counter of
    the entry if that is higher, and the fail counter and the token kind are kept.

    :param token: The token to update
    :param token_data: The entry of the YAML export for this token, without the owner
    """
    otp_count = token.token.count or 0
    fail_count = token.token.failcount
    token_kind = token.get_tokeninfo("tokenkind")
    token.update(token_data)
    exported_otp_count = token_data.get("counter")
    if exported_otp_count is not None:
        otp_count = max(otp_count, int(exported_otp_count))
    token.token.count = otp_count
    token.token.failcount = fail_count
    if token_kind:
        token.write_tokeninfo("tokenkind", token_kind)
    token.save()


@click.command("update")
@click.argument('yaml_file', type=click.File())
@with_appcontext
def updatetokens(yaml_file):
    """
    Update existing tokens in the privacyIDEA system. You must specify a YAML
    file with the tokendata.
    Can be used to reencrypt data, when changing the encryption key.
    The OTP counter and the fail counter of the tokens are kept.
    """
    click.echo("Loading YAML data. This may take a while.")
    token_list = yaml_safe_load(yaml_file.read())
    for tok in token_list:
        # The owner of an entry is not changed
        tok.pop("owner", None)
        serial = tok.get("serial")
        if not serial:
            # get_tokens() without a serial would return every token
            sys.stderr.write("\nSkipping an entry without a serial.\n")
            continue
        tok_objects = get_tokens(serial=serial)
        if len(tok_objects) == 0:
            sys.stderr.write(f"\nCan not find token {serial}. Not updating.\n")
        else:
            click.echo(f"Updating token {serial}.")
            try:
                _update_token_keeping_state(tok_objects[0], tok)
            except Exception as e:
                click.echo(f"\nFailed to update token {serial} ({e}).", err=True)
