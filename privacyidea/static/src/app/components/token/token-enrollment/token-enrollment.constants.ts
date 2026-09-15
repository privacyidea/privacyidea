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
 * Result value of an enrollment dialog whose enrollment was cancelled by the user.
 * The incomplete token has been deleted in that case.
 */
export const ENROLLMENT_CANCELLED = "enrollment-cancelled";

export type EnrollmentStepResult = EnrollmentResponse | typeof ENROLLMENT_CANCELLED | null;
