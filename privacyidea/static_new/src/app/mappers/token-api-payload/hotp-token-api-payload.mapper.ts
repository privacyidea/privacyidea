import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for HOTP-specific enrollment data
export interface HotpEnrollmentData extends TokenEnrollmentData {
  type: 'hotp';
  generateOnServer?: boolean;
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
}

@Injectable({ providedIn: 'root' })
export class HotpApiPayloadMapper
  implements TokenApiPayloadMapper<HotpEnrollmentData>
{
  toApiPayload(data: HotpEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): HotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as HotpEnrollmentData;
  }
}
