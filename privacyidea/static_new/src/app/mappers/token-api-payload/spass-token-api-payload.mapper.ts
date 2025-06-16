import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for SPASS-specific enrollment data
export interface SpassEnrollmentData extends TokenEnrollmentData {
  type: 'spass';
  // No type-specific fields identified from EnrollSpassComponent or TokenService handling
}

@Injectable({ providedIn: 'root' })
export class SpassApiPayloadMapper
  implements TokenApiPayloadMapper<SpassEnrollmentData>
{
  toApiPayload(data: SpassEnrollmentData): any {
    // Placeholder: Implement transformation to API payload.
    return { ...data };
  }

  fromApiPayload(payload: any): SpassEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as SpassEnrollmentData;
  }
}
