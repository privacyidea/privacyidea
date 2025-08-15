import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface HotpEnrollmentData extends TokenEnrollmentData {
  type: "hotp";
  generateOnServer?: boolean;
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
}

export interface HotpEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  otplen?: number;
  hashlib?: string;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class HotpApiPayloadMapper implements TokenApiPayloadMapper<HotpEnrollmentData> {
  toApiPayload(data: HotpEnrollmentData): HotpEnrollmentPayload {
    const payload: HotpEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      otpkey: data.generateOnServer ? null : (data.otpKey ?? null),
      genkey: data.generateOnServer ? 1 : 0,
      otplen: data.otpLength !== undefined ? Number(data.otpLength) : undefined,
      hashlib: data.hashAlgorithm,
      serial: data.serial ?? null
    };

    if (payload.otplen === undefined) delete payload.otplen;
    if (payload.hashlib === undefined) delete payload.hashlib;
    if (payload.serial === null) delete payload.serial;

    return payload;
  }

  fromApiPayload(payload: any): HotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as HotpEnrollmentData;
  }
}
