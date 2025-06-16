import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Push Token-specific enrollment data
export interface PushEnrollmentData extends TokenEnrollmentData {
  type: 'push';
  // No type-specific fields from EnrollmentOptions are directly used for params in TokenService.
  // genkey=1 is hardcoded.
}

export interface PushEnrollmentPayload extends TokenEnrollmentPayload {
  genkey: 1;
}

@Injectable({ providedIn: 'root' })
export class PushApiPayloadMapper
  implements TokenApiPayloadMapper<PushEnrollmentData>
{
  toApiPayload(data: PushEnrollmentData): PushEnrollmentPayload {
    return {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      genkey: 1, // Hardcoded as per switch statement
    };
  }

  fromApiPayload(payload: any): PushEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PushEnrollmentData;
  }
}
