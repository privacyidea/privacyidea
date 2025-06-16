import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Registration Token-specific enrollment data
export interface RegistrationEnrollmentData extends TokenEnrollmentData {
  type: 'registration';
}

export interface RegistrationEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: 'root' })
export class RegistrationApiPayloadMapper
  implements TokenApiPayloadMapper<RegistrationEnrollmentData>
{
  toApiPayload(data: RegistrationEnrollmentData): any {
    // Placeholder: Implement transformation to API payload.
    return { ...data };
  }

  fromApiPayload(payload: any): RegistrationEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as RegistrationEnrollmentData;
  }
}
