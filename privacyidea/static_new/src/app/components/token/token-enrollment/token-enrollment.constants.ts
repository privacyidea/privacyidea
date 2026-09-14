/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { MatTooltipDefaultOptions } from "@angular/material/tooltip";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

export const CUSTOM_TOOLTIP_OPTIONS: MatTooltipDefaultOptions = {
  showDelay: 500,
  touchLongPressShowDelay: 500,
  hideDelay: 0,
  touchendHideDelay: 0,
  disableTooltipInteractivity: true
};

/**
 * A list of token types that do should not show a QR code in the last enrollment step dialog.
 */
export const NO_QR_CODE_TOKEN_TYPES = [
  "certificate",
  "registration",
  "paper",
  "tan",
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
 * A list of token types that should not show a regenerate button in the last enrollment step dialog.
 */
export const NO_REGENERATE_TOKEN_TYPES = [
  "certificate",
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

/**
 * A list of token types that can only exist for a concrete user, because the server refuses
 * to create them without one.
 */
export const USER_REQUIRED_TOKEN_TYPES = ["tiqr", "webauthn", "passkey", "certificate"];

/**
 * A list of token types for which assigning to a realm without a user is not offered: every
 * type that requires a user, plus push, which is tied to one user's registered device.
 */
export const NO_REALM_ONLY_TOKEN_TYPES = [...USER_REQUIRED_TOKEN_TYPES, "push"];

/**
 * A list of token types whose last enrollment step shows data that exists nowhere else, so
 * that dialog must not be dismissible by a backdrop click or the escape key. For a
 * certificate it is the PKCS#12 passphrase, which the server never stores: losing it makes
 * the enrolled private key unusable.
 */
export const NO_DISMISS_LAST_STEP_TOKEN_TYPES = ["certificate"];

/**
 * Result value of an enrollment dialog whose enrollment was cancelled by the user.
 * The incomplete token has been deleted in that case.
 */
export const ENROLLMENT_CANCELLED = "enrollment-cancelled";

export type EnrollmentStepResult = EnrollmentResponse | typeof ENROLLMENT_CANCELLED | null;
