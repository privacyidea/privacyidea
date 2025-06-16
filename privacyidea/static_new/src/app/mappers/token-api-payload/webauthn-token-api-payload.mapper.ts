import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for WebAuthn-specific enrollment data
export interface WebAuthnEnrollmentData extends TokenEnrollmentData {
  type: 'webauthn';
  credential_id?: string;
}

export interface WebAuthnEnrollmentPayload extends TokenEnrollmentPayload {
  credential_id?: string; // If present, all fields from WebAuthnEnrollmentData are part of payload
}

@Injectable({ providedIn: 'root' })
export class WebAuthnApiPayloadMapper
  implements TokenApiPayloadMapper<WebAuthnEnrollmentData>
{
  toApiPayload(data: WebAuthnEnrollmentData): WebAuthnEnrollmentPayload {
    const payload: WebAuthnEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
    };

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
