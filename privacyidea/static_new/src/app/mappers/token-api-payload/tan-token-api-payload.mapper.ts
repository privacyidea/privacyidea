import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for TAN Token-specific enrollment data
export interface TanEnrollmentData extends TokenEnrollmentData {
  type: 'tan';
  tanCount?: number; // Corresponds to 'tancount' in EnrollTanComponent
  tanLength?: number; // Corresponds to 'tanlength' in EnrollTanComponent
}

export interface TanEnrollmentPayload extends TokenEnrollmentPayload {
  tancount?: number;
  tanlength?: number;
}

@Injectable({ providedIn: 'root' })
export class TanApiPayloadMapper
  implements TokenApiPayloadMapper<TanEnrollmentData>
{
  toApiPayload(data: TanEnrollmentData): TanEnrollmentPayload {
    // 'tan' type is not in the main switch statement.
    // Mapping based on defined interfaces.
    const payload: TanEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      tancount: data.tanCount,
      tanlength: data.tanLength,
    };
    if (payload.tancount === undefined) delete payload.tancount;
    if (payload.tanlength === undefined) delete payload.tanlength;
    return payload;
  }

  fromApiPayload(payload: any): TanEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return {
      ...payload,
      tanCount: payload.tancount,
      tanLength: payload.tanlength,
    } as TanEnrollmentData;
  }
}
