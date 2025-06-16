import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for mOTP-specific enrollment data
export interface MotpEnrollmentData extends TokenEnrollmentData {
  type: 'motp';
  generateOnServer?: boolean;
  otpKey?: string;
  motpPin?: string;
}

@Injectable({ providedIn: 'root' })
export class MotpApiPayloadMapper
  implements TokenApiPayloadMapper<MotpEnrollmentData>
{
  toApiPayload(data: MotpEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): MotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as MotpEnrollmentData;
  }
}
