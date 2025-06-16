import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Vasco Token-specific enrollment data
export interface VascoEnrollmentData extends TokenEnrollmentData {
  type: 'vasco';
  useVascoSerial?: boolean;
  vascoSerial?: string; // Used if useVascoSerial is true
  otpKey?: string;
  // genkey=0 is hardcoded in TokenService
}

@Injectable({ providedIn: 'root' })
export class VascoApiPayloadMapper
  implements TokenApiPayloadMapper<VascoEnrollmentData>
{
  toApiPayload(data: VascoEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): VascoEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as VascoEnrollmentData;
  }
}
