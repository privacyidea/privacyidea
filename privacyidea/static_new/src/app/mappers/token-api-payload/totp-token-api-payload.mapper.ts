import { Injectable } from "@angular/core";
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

export interface TotpEnrollmentData extends TokenEnrollmentData {
  type: "totp";
  generateOnServer?: boolean;
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
  timeStep?: number;
}

export interface TotpEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  otplen?: number;
  hashlib?: string;
  timeStep?: number;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class TotpApiPayloadMapper implements TokenApiPayloadMapper<TotpEnrollmentData> {
  toApiPayload(data: TotpEnrollmentData): TotpEnrollmentPayload {
    const payload: TotpEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      otpkey: data.generateOnServer ? null : (data.otpKey ?? null),
      genkey: data.generateOnServer ? 1 : 0,
      otplen: data.otpLength !== undefined ? Number(data.otpLength) : undefined,
      hashlib: data.hashAlgorithm,
      timeStep: data.timeStep !== undefined ? Number(data.timeStep) : undefined,
      serial: data.serial ?? null
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.otplen === undefined) delete payload.otplen;
    if (payload.hashlib === undefined) delete payload.hashlib;
    if (payload.timeStep === undefined) delete payload.timeStep;
    if (payload.serial === null) delete payload.serial;

    return payload;
  }

  fromApiPayload(payload: any): TotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as TotpEnrollmentData;
  }
}
