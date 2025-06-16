import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Passkey-specific enrollment data
export interface PasskeyEnrollmentData extends TokenEnrollmentData {
  type: 'passkey';
  credential_id?: string;
}

@Injectable({ providedIn: 'root' })
export class PasskeyApiPayloadMapper
  implements TokenApiPayloadMapper<PasskeyEnrollmentData>
{
  toApiPayload(data: PasskeyEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): PasskeyEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PasskeyEnrollmentData;
  }
}
