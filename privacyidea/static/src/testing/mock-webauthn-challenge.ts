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
import { MultiChallenge, WebAuthnSignRequest } from "@services/auth/auth.service";

export function mockWebAuthnSignRequest(
  credentialId: string,
  overrides: Partial<WebAuthnSignRequest> = {}
): WebAuthnSignRequest {
  return {
    allowCredentials: [{ id: credentialId, transports: ["usb", "nfc"], type: "public-key" }],
    challenge: "shared-transaction-challenge",
    rpId: "example.com",
    timeout: 60000,
    userVerification: "preferred",
    ...overrides
  };
}

export function mockWebAuthnChallenge(serial: string, signRequest: WebAuthnSignRequest): MultiChallenge {
  return {
    attributes: { webAuthnSignRequest: signRequest },
    client_mode: "webauthn",
    message: `Please confirm with your WebAuthn token (${serial})`,
    serial,
    transaction_id: "tx-webauthn",
    type: "webauthn"
  };
}
