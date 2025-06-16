import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for WebAuthn-specific enrollment data
export interface WebAuthnEnrollmentData extends TokenEnrollmentData {
  type: 'webauthn';
  credential_id?: string;
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
