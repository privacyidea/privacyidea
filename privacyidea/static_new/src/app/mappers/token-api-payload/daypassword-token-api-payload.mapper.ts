import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for DayPassword-specific enrollment data
export interface DaypasswordEnrollmentData extends TokenEnrollmentData {
  type: 'daypassword';
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
  timeStep?: number;
}

@Injectable({ providedIn: 'root' })
export class DaypasswordApiPayloadMapper
  implements TokenApiPayloadMapper<DaypasswordEnrollmentData>
{
  toApiPayload(data: DaypasswordEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): DaypasswordEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as DaypasswordEnrollmentData;
  }
}
