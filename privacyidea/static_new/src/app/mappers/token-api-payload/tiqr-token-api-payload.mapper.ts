import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for TIQR Token-specific enrollment data
export interface TiqrEnrollmentData extends TokenEnrollmentData {
  type: 'tiqr';
  // No type-specific fields identified from EnrollTiqrComponent or TokenService handling
}

export interface TiqrEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: 'root' })
export class TiqrApiPayloadMapper
  implements TokenApiPayloadMapper<TiqrEnrollmentData>
{
  toApiPayload(data: TiqrEnrollmentData): any {
    // Placeholder: Implement transformation to API payload.
    return { ...data };
  }

  fromApiPayload(payload: any): TiqrEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as TiqrEnrollmentData;
  }
}
