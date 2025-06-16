import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for SPASS-specific enrollment data
export interface SpassEnrollmentData extends TokenEnrollmentData {
  type: 'spass';
  // No type-specific fields identified from EnrollSpassComponent or TokenService handling
}

export interface SpassEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: 'root' })
export class SpassApiPayloadMapper
  implements TokenApiPayloadMapper<SpassEnrollmentData>
{
  toApiPayload(data: SpassEnrollmentData): SpassEnrollmentPayload {
    // No type-specific fields in switch statement for 'spass'
    return {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
    };
  }

  fromApiPayload(payload: any): SpassEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as SpassEnrollmentData;
  }
}
