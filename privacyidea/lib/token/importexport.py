# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bulk import and export of tokens."""

import logging
from dataclasses import dataclass

from privacyidea.lib.error import ParameterError
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import Token, db

from privacyidea.lib.token.query import create_tokenclass_object, get_one_token

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenImportResult:
    successful_tokens: list[str]
    updated_tokens: list[str]
    # Serials of tokens that could not be imported. A None entry marks a malformed
    # source entry that had no serial to report.
    failed_tokens: list[str | None]


@dataclass(frozen=True)
class TokenExportResult:
    """Result of a bulk token export operation."""
    successful_tokens: list[dict]  # List of token dicts as returned by TokenClass.export_token()
    failed_tokens: list[str]  # List of serial numbers of tokens for which the export failed


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
            # No serial to report for this entry; None marks a malformed entry in the result
            failed_tokens.append(None)
            continue

        existing_token = get_one_token(serial=serial, silent_fail=True)
        # We check if there is no existing token or if we want to update existing tokens
        if not existing_token or update_existing_tokens:
            created = False
            # We create a new token, if there is no existing token
            if not existing_token:
                # A type is only required when creating a new token; updates may omit it
                token_type = token_info_dict.get("type")
                if not token_type:
                    log.error(f"Token entry for serial {serial} is missing a type. Skipping.")
                    failed_tokens.append(serial)
                    continue
                try:
                    db_token = Token(serial, tokentype=token_type.lower())
                    db_token.save()
                    created = True
                    token = create_tokenclass_object(db_token)
                except Exception as e:
                    log.error(f"Could not create token {serial}: {e}")
                    failed_tokens.append(serial)
                    # Remove the row if it was already persisted before the failure
                    if created:
                        db_token.delete()
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


def update_token_from_export(token_data: dict) -> str:
    """
    Write an entry of a token export, e.g. the YAML export of the token janitors, to the existing token with the
    same serial. This re-encrypts the secrets of the token with the current encryption key.

    TokenClass.update() stores the OTP key as a new key, which resets the OTP counter and the fail counter and marks
    the token as a software token. The OTP key of an export entry is the key the token already has, so the rest is
    put back, also if update() fails after the reset: the fail counter and the token kind keep their values, and
    the OTP counter keeps its value or takes the counter of the entry, if that is higher. A lower OTP counter would
    make OTP values the token has already used valid again. The owner of the entry is ignored.

    If update() fails, the changes it has not committed yet are discarded. update() commits in between, e.g. when it
    writes token info, so the changes committed before the error remain.

    :param token_data: the entry of the export
    :return: the serial of the updated token
    :raises ParameterError: if the entry has no serial or its counter is not a number
    :raises ResourceNotFoundError: if there is no token with the serial of the entry
    """
    serial = token_data.get("serial")
    if not serial:
        # Looking the token up without a serial would find every token
        raise ParameterError("The entry has no serial.")
    token = get_one_token(serial=serial)
    token_data = {key: value for key, value in token_data.items() if key != "owner"}
    otp_count = token.token.count or 0
    fail_count = token.token.failcount
    token_kind = token.get_tokeninfo("tokenkind")
    exported_otp_count = token_data.get("counter")
    if exported_otp_count not in (None, ""):
        # Checked before the token is changed, the counter is put back after the update
        try:
            otp_count = max(otp_count, int(exported_otp_count))
        except (TypeError, ValueError):
            raise ParameterError(f"The counter {exported_otp_count!r} of the entry is not a number")
    try:
        token.update(token_data)
    except Exception:
        db.session.rollback()
        raise
    finally:
        token.token.count = otp_count
        token.token.failcount = fail_count
        if token_kind:
            token.write_tokeninfo("tokenkind", token_kind, commit_db_session=False)
        token.save()
    return serial

