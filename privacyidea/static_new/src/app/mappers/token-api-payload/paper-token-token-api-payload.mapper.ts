import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for Papertoken-specific enrollment data
export interface PaperTokenEnrollmentData extends TokenEnrollmentData {
  type: "papertoken";
  otpLength?: number;
  otpCount?: number; // Number of OTPs to generate for the paper token
}

export interface PaperTokenEnrollmentPayload extends TokenEnrollmentPayload {
  otplen?: number; // Assuming API field name if different from otpLength
  otpcount?: number; // Assuming API field name if different from otpCount
}

@Injectable({ providedIn: "root" })
export class PaperTokenApiPayloadMapper implements TokenApiPayloadMapper<PaperTokenEnrollmentData> {
  toApiPayload(data: PaperTokenEnrollmentData): PaperTokenEnrollmentPayload {
    // 'papertoken' type is not in the main switch statement.
    // Mapping based on defined interfaces.
    const payload: PaperTokenEnrollmentPayload = {
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

  fromApiPayload(payload: any): PaperTokenEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PaperTokenEnrollmentData;
  }
}
