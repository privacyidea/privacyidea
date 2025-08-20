import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

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
      realm: data.user? data.realm : null,
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
