import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Paper Token-specific enrollment data (distinct from 'papertoken')
export interface PaperEnrollmentData extends TokenEnrollmentData {
  type: 'paper';
  otpLength?: number; // Corresponds to 'otplen' in EnrollPaperComponent
  otpCount?: number; // Corresponds to 'otpcount' in EnrollPaperComponent
}

export interface PaperEnrollmentPayload extends TokenEnrollmentPayload {
  otplen?: number;
  otpcount?: number;
}

@Injectable({ providedIn: 'root' })
export class PaperApiPayloadMapper
  implements TokenApiPayloadMapper<PaperEnrollmentData>
{
  toApiPayload(data: PaperEnrollmentData): PaperEnrollmentPayload {
    // 'paper' type is not in the main switch statement.
    // Mapping based on defined interfaces and component behavior.
    const payload: PaperEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      otplen: data.otpLength,
      otpcount: data.otpCount,
    };
    if (payload.otplen === undefined) delete payload.otplen;
    if (payload.otpcount === undefined) delete payload.otpcount;
    return payload;
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
