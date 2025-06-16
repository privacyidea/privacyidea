import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Papertoken-specific enrollment data
export interface PaperTokenEnrollmentData extends TokenEnrollmentData {
  type: 'papertoken';
  otpLength?: number;
  otpCount?: number; // Number of OTPs to generate for the paper token
}

@Injectable({ providedIn: 'root' })
export class PaperTokenApiPayloadMapper
  implements TokenApiPayloadMapper<PaperTokenEnrollmentData>
{
  toApiPayload(data: PaperTokenEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): PaperTokenEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PaperTokenEnrollmentData;
  }
}
