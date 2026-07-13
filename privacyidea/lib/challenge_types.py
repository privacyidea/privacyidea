# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Pure challenge session/status definitions with no dependencies on the ORM
models or the token business logic.

They live in their own leaf module so both the DB-backed ``Challenge``
(privacyidea.models.challenge) and the Redis ``ChallengeDTO``
(privacyidea.lib.cache.redis) can import them at module level without a
circular import: ``lib.tokenclass`` imports ``models``, so hosting these here
(rather than in ``tokenclass``) is what lets ``models`` reach them.
``lib.tokenclass`` re-exports them for backwards compatibility, so
``from privacyidea.lib.tokenclass import ChallengeSession`` keeps working.
"""


class ChallengeSession:
    ENROLLMENT = "enrollment"
    DECLINED = "challenge_declined"
    CANCELLED = "challenge_cancelled"


# Maps a refused challenge session to the challenge_status string reported to clients and the
# audit log. Single source of truth shared by the push answer scan and /validate/polltransaction.
# Insertion order defines the reporting precedence: "declined" (the user actively rejected a
# challenge they did not trigger) outranks "cancelled" (self-abort) as the higher-suspicion signal.
CHALLENGE_REFUSAL_STATUS = {
    ChallengeSession.DECLINED: "declined",
    ChallengeSession.CANCELLED: "cancelled",
}
# The challenge sessions that count as "refused" - i.e. not open. Derived from the mapping above so
# a new refusal reason only has to be added in one place.
CHALLENGE_REFUSAL_SESSIONS = frozenset(CHALLENGE_REFUSAL_STATUS)


def is_challenge_open(is_valid: bool, otp_valid: bool, session: str) -> bool:
    """
    Whether a challenge can still be answered: it is still valid (not expired), has not been
    answered yet and has not been refused. Shared by both challenge backends (the DB-backed
    ``Challenge`` and the Redis ``ChallengeDTO``) so their ``is_open()`` cannot drift apart.
    """
    return is_valid and not otp_valid and session not in CHALLENGE_REFUSAL_SESSIONS
