import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

export interface SpassEnrollmentData extends TokenEnrollmentData {
  type: 'spass';
}

export interface SpassEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: 'root' })
export class SpassApiPayloadMapper
  implements TokenApiPayloadMapper<SpassEnrollmentData>
{
  toApiPayload(data: SpassEnrollmentData): SpassEnrollmentPayload {
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
