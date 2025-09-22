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
import { Injectable } from "@angular/core";
import { WebAuthnRegisterRequest } from "../../services/token/token.service";
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";

export interface WebauthnEnrollmentResponse extends EnrollmentResponse<WebauthnEnrollmentResponseDetail> {}

export interface WebauthnEnrollmentResponseDetail extends EnrollmentResponseDetail {
  webAuthnRegisterRequest: WebAuthnRegisterRequest;
}

// Interface for the initialization options of the WebAuthn token (init step)
export interface WebAuthnEnrollmentData extends TokenEnrollmentData {
  type: "webauthn";
  credential_id?: string;
}

// Interface for the finalization data of the WebAuthn enrollment (final step)
// This is the data sent to privacyIDEA after the user has interacted with the browser to create a credential.
export interface WebauthnFinalizeData extends WebAuthnEnrollmentData {
  transaction_id: string;
  serial: string;
  credential_id: string; // The ID of the credential created
  rawId: string; // Base64-encoded raw ID of the credential
  authenticatorAttachment: string | null; // Attachment type of the authenticator (e.g, 'platform', 'cross-platform', or null)
  regdata: string; // Base64-encoded attestation object
  clientdata: string; // Base64-encoded client data JSON
  credProps?: any; // Optional credential properties, if available
}

export interface WebAuthnEnrollmentPayload extends TokenEnrollmentPayload {
  credential_id?: string; // If present, all fields from WebAuthnEnrollmentData are part of payload
}

export interface WebAuthnFinalizePayload extends TokenEnrollmentPayload {
  credential_id: string;
  regdata: string;
  clientdata: string;
  transaction_id: string;
  serial: string;
  rawId: string;
  authenticatorAttachment: string | null;
  credProps?: any;
}

@Injectable({ providedIn: "root" })
export class WebAuthnApiPayloadMapper implements TokenApiPayloadMapper<WebAuthnEnrollmentData> {
  toApiPayload(data: WebAuthnEnrollmentData): WebAuthnEnrollmentPayload {
    const payload: WebAuthnEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    if (data.credential_id) {
      // Switch logic copies all of `data` if credential_id is present.
      // Adhering to WebAuthnEnrollmentPayload which only adds credential_id.
      payload.credential_id = data.credential_id;
    }

    if (payload.credential_id === undefined) delete payload.credential_id;
    return payload;
  }

  fromApiPayload(payload: any): WebAuthnEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as WebAuthnEnrollmentData;
  }
}

@Injectable({ providedIn: "root" })
export class WebAuthnFinalizeApiPayloadMapper implements TokenApiPayloadMapper<WebauthnFinalizeData> {
  toApiPayload(data: WebauthnFinalizeData): WebAuthnFinalizePayload {
    const payload: WebAuthnFinalizePayload = {
      type: data.type,
      serial: data.serial,
      credential_id: data.credential_id,
      regdata: data.regdata,
      clientdata: data.clientdata,
      transaction_id: data.transaction_id,
      rawId: data.rawId,
      authenticatorAttachment: data.authenticatorAttachment || null
    };

    if (data.credProps) payload.credProps = data.credProps;

    return payload;
  }

  fromApiPayload(payload: any): WebauthnFinalizeData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as WebauthnFinalizeData;
  }
}
