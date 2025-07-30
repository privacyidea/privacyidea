import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

export interface VascoEnrollmentData extends TokenEnrollmentData {
  type: 'vasco';
  useVascoSerial?: boolean;
  vascoSerial?: string;
  otpKey?: string;
}

export interface VascoEnrollmentPayload extends TokenEnrollmentPayload {
  serial?: string;
  otpkey?: string;
  genkey: 0;
}

@Injectable({ providedIn: 'root' })
export class VascoApiPayloadMapper
  implements TokenApiPayloadMapper<VascoEnrollmentData>
{
  toApiPayload(data: VascoEnrollmentData): VascoEnrollmentPayload {
    const payload: VascoEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      genkey: 0,
      otpkey: data.otpKey,
    };

    if (data.useVascoSerial) {
      payload.serial = data.vascoSerial;
    }

    if (payload.serial === undefined) delete payload.serial;
    if (payload.otpkey === undefined) delete payload.otpkey;

    return payload;
  }

  fromApiPayload(payload: any): VascoEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as VascoEnrollmentData;
  }
}
