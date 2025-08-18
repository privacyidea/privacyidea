import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for Passkey-specific enrollment data
export interface PasskeyEnrollmentData extends TokenEnrollmentData {
  type: "passkey";
  credential_id?: string;
}

export interface PasskeyEnrollmentPayload extends TokenEnrollmentPayload {
  credential_id?: string; // If present, all fields from PasskeyEnrollmentData are part of payload
}

@Injectable({ providedIn: "root" })
export class PasskeyApiPayloadMapper implements TokenApiPayloadMapper<PasskeyEnrollmentData> {
  toApiPayload(data: PasskeyEnrollmentData): PasskeyEnrollmentPayload {
    const payload: PasskeyEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin
    };

    if (data.credential_id) {
      // Switch logic copies all of `data` if credential_id is present.
      // Adhering to PasskeyEnrollmentPayload which only adds credential_id.
      payload.credential_id = data.credential_id;
    }

    if (payload.credential_id === undefined) delete payload.credential_id;
    return payload;
  }

  fromApiPayload(payload: any): PasskeyEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PasskeyEnrollmentData;
  }
}
