import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for SMS Token-specific enrollment data
export interface SmsEnrollmentData extends TokenEnrollmentData {
  type: 'sms';
  smsGateway?: string; // Mapped to 'sms.identifier'
  phoneNumber?: string;
  readNumberDynamically?: boolean; // Mapped to 'dynamic_phone'
}

export interface SmsEnrollmentPayload extends TokenEnrollmentPayload {
  'sms.identifier'?: string;
  phone: string | null;
  dynamic_phone?: boolean;
}

@Injectable({ providedIn: 'root' })
export class SmsApiPayloadMapper
  implements TokenApiPayloadMapper<SmsEnrollmentData>
{
  toApiPayload(data: SmsEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): SmsEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as SmsEnrollmentData;
  }
}
