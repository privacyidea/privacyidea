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
      realm: data.user? data.realm : null,
      pin: data.pin,
      otplen: data.otpLength,
      otpcount: data.otpCount
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.otplen === undefined) delete payload.otplen;
    if (payload.otpcount === undefined) delete payload.otpcount;
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
