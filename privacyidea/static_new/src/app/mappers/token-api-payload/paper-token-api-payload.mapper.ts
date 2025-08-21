import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface PaperEnrollmentData extends TokenEnrollmentData {
  type: "paper";
  otpLength?: number;
  otpCount?: number;
}

export interface PaperEnrollmentPayload extends TokenEnrollmentPayload {
  otplen?: number;
  otpcount?: number;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class PaperApiPayloadMapper implements TokenApiPayloadMapper<PaperEnrollmentData> {
  toApiPayload(data: PaperEnrollmentData): PaperEnrollmentPayload {
    const payload: PaperEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      otplen: data.otpLength,
      otpcount: data.otpCount,
      serial: data.serial ?? null
    };
    if (payload.otplen === undefined) delete payload.otplen;
    if (payload.otpcount === undefined) delete payload.otpcount;
    if (payload.serial === null) delete payload.serial;
    return payload;
  }

  fromApiPayload(payload: any): PaperEnrollmentData {
    return {
      ...payload,
      otpLength: payload.otplen,
      otpCount: payload.otpcount
    } as PaperEnrollmentData;
  }
}
