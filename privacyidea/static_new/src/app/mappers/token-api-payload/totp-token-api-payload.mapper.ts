import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for TOTP-specific enrollment data
export interface TotpEnrollmentData extends TokenEnrollmentData {
  type: 'totp';
  generateOnServer?: boolean;
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
  timeStep?: number;
}

@Injectable({ providedIn: 'root' })
export class TotpApiPayloadMapper
  implements TokenApiPayloadMapper<TotpEnrollmentData>
{
  toApiPayload(data: TotpEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): TotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as TotpEnrollmentData;
  }
}
