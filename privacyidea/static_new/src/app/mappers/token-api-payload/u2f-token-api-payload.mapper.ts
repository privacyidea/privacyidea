import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for U2F Token-specific enrollment data
export interface U2fEnrollmentData extends TokenEnrollmentData {
  type: 'u2f';
  // Specific U2F parameters (like u2fRegisterRequest) are handled post-initial enrollment
  // or would be part of a more complex payload structure if this mapper handled the full flow.
}

export interface U2fEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: 'root' })
export class U2fApiPayloadMapper
  implements TokenApiPayloadMapper<U2fEnrollmentData>
{
  toApiPayload(data: U2fEnrollmentData): any {
    // Placeholder: Implement transformation to API payload for the initial init call.
    return { ...data };
  }

  fromApiPayload(payload: any): U2fEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as U2fEnrollmentData;
  }
}
