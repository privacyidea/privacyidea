import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Application Specific Password enrollment data
export interface ApplspecEnrollmentData extends TokenEnrollmentData {
  type: 'applspec';
  generateOnServer?: boolean;
  otpKey?: string;
  serviceId?: string;
}

export interface ApplspecEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  service_id?: string;
}

@Injectable({ providedIn: 'root' })
export class ApplspecApiPayloadMapper
  implements TokenApiPayloadMapper<ApplspecEnrollmentData>
{
  toApiPayload(data: ApplspecEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): ApplspecEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as ApplspecEnrollmentData;
  }
}
