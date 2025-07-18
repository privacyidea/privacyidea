import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Vasco Token-specific enrollment data
export interface VascoEnrollmentData extends TokenEnrollmentData {
  type: 'vasco';
  useVascoSerial?: boolean;
  vascoSerial?: string; // Used if useVascoSerial is true
  otpKey?: string;
  // genkey=0 is hardcoded in TokenService
}

export interface VascoEnrollmentPayload extends TokenEnrollmentPayload {
  serial?: string; // This is the Vasco device serial, conditionally set
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
      genkey: 0, // Hardcoded as per switch statement
      // otpkey is always set from data.otpKey as per switch (will be undefined if useVascoSerial is true, based on component logic)
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
