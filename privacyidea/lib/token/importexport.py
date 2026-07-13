# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bulk import and export of tokens."""

import logging
from dataclasses import dataclass

from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import (Token)

from privacyidea.lib.token.query import create_tokenclass_object, get_one_token

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenImportResult:
    successful_tokens: list[str]
    updated_tokens: list[str]
    failed_tokens: list[str]


@dataclass(frozen=True)
class TokenExportResult:
    successful_tokens: list[str]  # The serialized tokens for which the export succeeded
    failed_tokens: list[str]  # The serial of tokens for which the export failed


def export_tokens(tokens: list[TokenClass], export_user: bool = True) -> TokenExportResult:
    """
    Export a list of tokens.
    """
    success = []
    failed = []
    for token in tokens:
        try:
            exported = token.export_token(export_user=export_user)
            success.append(exported)
        except Exception as ex:
            log.error(f"Failed to export token {token.get_serial()}: {ex}")
            failed.append(token.get_serial())
    return TokenExportResult(successful_tokens=success, failed_tokens=failed)


def import_tokens(tokens: list[dict], update_existing_tokens: bool = True,
                  assign_to_user: bool = True) -> TokenImportResult:
    """
    Import a list of token dictionaries.

    :param tokens: list of dict with token information
    :param update_existing_tokens: If True, existing tokens will be updated with the new data.
    :param assign_to_user: If True, the user from the token data will be assigned to the token.
    :return: list of token objects
    """
    successful_tokens = []
    updated_tokens = []
    failed_tokens = []

    for token_info_dict in tokens:
        serial = token_info_dict.get("serial")

        # Validate serial early
        if not serial:
            log.error("Token entry is missing a serial number. Skipping.")
            failed_tokens.append('token with missing serial')
            continue

        # Validate type early
        token_type = token_info_dict.get("type")
        if not token_type:
            log.error(f"Token entry for serial {serial} is missing a type. Skipping.")
            failed_tokens.append(serial)
            continue

        existing_token = get_one_token(serial=serial, silent_fail=True)
        # We check if there is no existing token or if we want to update existing tokens
        if not existing_token or update_existing_tokens:
            created = False
            # We create a new token, if there is no existing token
            if not existing_token:
                try:
                    db_token = Token(serial, tokentype=token_type.lower())
                    db_token.save()
                    token = create_tokenclass_object(db_token)
                    created = True
                except Exception as e:
                    log.error(f"Could not create token {serial}: {e}")
                    failed_tokens.append(serial)
                    continue
            # We use the existing token and update it
            else:
                token = existing_token

            # Assign the user, if wanted and if there is a user in the token info dict
            if assign_to_user and token_info_dict.get("user"):
                try:
                    owner = User(login=token_info_dict.get("user").get("login"),
                                 resolver=token_info_dict.get("user").get("resolver"),
                                 realm=token_info_dict.get("user").get("realm"),
                                 uid=token_info_dict.get("user").get("uid"))
                    token.add_user(owner, override=True)
                except Exception as e:
                    log.error(f"Could not assign user to token {serial}: {e}. "
                              f"The token will not be imported.")
                    failed_tokens.append(serial)
                    if created:
                        token.delete_token()
                    continue
            try:
                token.import_token(token_info_dict)
            except Exception as e:
                log.exception(f"Could not import token {serial}: {e}")
                failed_tokens.append(serial)
                if created:
                    token.delete_token()
                continue

            if not existing_token:
                successful_tokens.append(serial)
            else:
                updated_tokens.append(serial)
        else:
            log.info(f"Token with serial {serial} already exists.")
            failed_tokens.append(serial)
    return TokenImportResult(successful_tokens=successful_tokens, updated_tokens=updated_tokens,
                             failed_tokens=failed_tokens)
