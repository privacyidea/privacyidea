/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
/**
 * A list of token types that do should not show a QR code in the last enrollment step dialog.
 */
export const NO_QR_CODE_TOKEN_TYPES = [
  "registration",
  "paper",
  "tan",
  "spass",
  "email",
  "yubico",
  "yubikey",
  "sms",
  "applspec",
  "indexedsecret"
];

/**
 * A list of token types that should not show a regenerate button in the last enrollment step dialog.
 */
export const NO_REGENERATE_TOKEN_TYPES = [
  "registration",
  "spass",
  "email",
  "yubico",
  "yubikey",
  "sms",
  "applspec",
  "indexedsecret",
  "webauthn",
  "passkey"
];

/**
 * A list of token types for which the regenerate button should show "Values" instead of "QR Code".
 */
export const REGENERATE_AS_VALUES_TOKEN_TYPES = ["paper", "tan"];