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
  toApiPayload(data: WebAuthnEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): WebAuthnEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as WebAuthnEnrollmentData;
  }
}
