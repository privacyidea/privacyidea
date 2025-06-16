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
  toApiPayload(data: TanEnrollmentData): any {
    // Placeholder: Implement transformation to API payload.
    // EnrollTanComponent uses 'tancount' and 'tanlength'.
    return { ...data, tancount: data.tanCount, tanlength: data.tanLength };
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
