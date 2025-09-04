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
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

// Interface for Passkey-specific enrollment data
export interface PasskeyEnrollmentData extends TokenEnrollmentData {
  type: "passkey";
}

export interface PasskeyFinalizeData extends PasskeyEnrollmentData {
  credential_id: string;
  attestationObject: string;
  clientDataJSON: string;
  rawId: string;
  authenticatorAttachment: string | null;
  transaction_id: string;
  serial: string;
  credProps?: any;
}

export interface PasskeyFinalizationPayload extends TokenEnrollmentPayload {
  credential_id: string; // If present, all fields from PasskeyEnrollmentData are part of payload
  attestationObject: string;
  clientDataJSON: string;
  rawId: string;
  authenticatorAttachment: string | null;
  transaction_id: string;
  serial: string | null;
  credProps?: any;
}

@Injectable({ providedIn: "root" })
export class PasskeyApiPayloadMapper implements TokenApiPayloadMapper<PasskeyEnrollmentData> {
  toApiPayload(data: PasskeyEnrollmentData): TokenEnrollmentPayload {
    const payload: TokenEnrollmentPayload = {
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
    return payload;
  }

  fromApiPayload(payload: any): PasskeyEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PasskeyEnrollmentData;
  }
}

@Injectable({ providedIn: "root" })
export class PasskeyFinalizeApiPayloadMapper implements TokenApiPayloadMapper<PasskeyFinalizeData> {
  toApiPayload(data: PasskeyFinalizeData): PasskeyFinalizationPayload {
    const payload: PasskeyFinalizationPayload = {
      type: data.type,
      serial: data.serial,
      credential_id: data.credential_id,
      attestationObject: data.attestationObject,
      clientDataJSON: data.clientDataJSON,
      rawId: data.rawId,
      authenticatorAttachment: data.authenticatorAttachment,
      transaction_id: data.transaction_id
    };

    if (data.credProps) payload.credProps = data.credProps;

    return payload;
  }

  fromApiPayload(payload: any): PasskeyFinalizeData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PasskeyFinalizeData;
  }
}
