import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Paper Token-specific enrollment data (distinct from 'papertoken')
export interface PaperEnrollmentData extends TokenEnrollmentData {
  type: 'paper';
  otpLength?: number; // Corresponds to 'otplen' in EnrollPaperComponent
  otpCount?: number; // Corresponds to 'otpcount' in EnrollPaperComponent
}

@Injectable({ providedIn: 'root' })
export class PaperApiPayloadMapper
  implements TokenApiPayloadMapper<PaperEnrollmentData>
{
  toApiPayload(data: PaperEnrollmentData): any {
    // Placeholder: Implement transformation to API payload.
    // EnrollPaperComponent uses 'otplen' and 'otpcount'.
    return { ...data, otplen: data.otpLength, otpcount: data.otpCount };
  }

  fromApiPayload(payload: any): PaperEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return {
      ...payload,
      otpLength: payload.otplen,
      otpCount: payload.otpcount,
    } as PaperEnrollmentData;
  }
}
