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
  toApiPayload(data: SmsEnrollmentData): SmsEnrollmentPayload {
    const payload: SmsEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      'sms.identifier': data.smsGateway,
      phone: data.readNumberDynamically ? null : (data.phoneNumber ?? null),
      dynamic_phone: data.readNumberDynamically,
    };

    if (payload['sms.identifier'] === undefined) {
      delete payload['sms.identifier'];
    }
    if (payload.dynamic_phone === undefined) {
      // Should always be boolean due to component
      delete payload.dynamic_phone;
    }
    return payload;
  }

  fromApiPayload(payload: any): SmsEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as SmsEnrollmentData;
  }
}
