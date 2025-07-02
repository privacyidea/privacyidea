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

from flask.cli import AppGroup
import click
from privacyidea.lib.token import import_token

importtokens_cli = AppGroup("import", help="Import tokens from different sources.")


@importtokens_cli.command()
@click.argument('pskc_file', type=click.File())
@click.option('--preshared_key',
              help='The AES encryption key.')
@click.option('--validate_mac', type=click.Choice(['no_check', 'check_fail_soft', 'check_fail_hard']),
              default='check_fail_hard',
              help="""\b
              How the file should be validated.
              'no_check': Every token is parsed, ignoring HMAC
              'check_fail_soft': Skip tokens with invalid HMAC
              'check_fail_hard': Only import tokens if all HMAC are valid.""")
def pskc(pskc_file, preshared_key, validate_mac):
    """
    Loads token data from the PSKC_FILE.
    """
    from privacyidea.lib.importotp import parsePSKCdata

    file_contents = pskc_file.read()

    tokens, not_parsed_tokens = parsePSKCdata(file_contents,
                                              preshared_key_hex=preshared_key,
                                              validate_mac=validate_mac)
    success = 0
    failed = 0
    failed_tokens = []
    for serial in tokens:
        try:
            print(f"Importing token {serial}")
            import_token(serial, tokens[serial])
            success = success + 1
        except Exception as e:
            failed = failed + 1
            failed_tokens.append(serial)
            print(f"--- Failed to import token. {e}")

    if not_parsed_tokens:
        print(f"The following tokens were not read from the PSKC file"
              f" because they could not be validated: {not_parsed_tokens}")
    print(f"Successfully imported {success} tokens.")
    print(f"Failed to import {failed} tokens: {failed_tokens}")
