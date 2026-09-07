# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared constants for the token library package."""

ENCODING = "utf-8"

# Configuration to generate a complete random serial
PI_TOKEN_SERIAL_RANDOM = "PI_TOKEN_SERIAL_RANDOM"  # nosec B105

B32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

# Token info key on a replacement token of the lost token process, holding the serial of the
# token it replaces. It links the replacements of a token together, so that an earlier one can
# be disabled when a new one is issued.
LOST_TOKEN_FOR = "lost_token_for"  # nosec B105
