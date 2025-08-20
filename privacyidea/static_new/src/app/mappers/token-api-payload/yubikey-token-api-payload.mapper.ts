import { Injectable } from "@angular/core";
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

export interface YubikeyEnrollmentData extends TokenEnrollmentData {
  type: "yubikey";
  otpKey: string | null;
  otpLength: number | null;
}

export interface YubikeyEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  otplen: number | null;
}

@Injectable({ providedIn: "root" })
export class YubikeyApiPayloadMapper implements TokenApiPayloadMapper<YubikeyEnrollmentData> {
  toApiPayload(data: YubikeyEnrollmentData): YubikeyEnrollmentPayload {
    return {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      // otpLength from component is number | null. Payload otplen is number | null.
      otplen: data.otpLength,
      // otpKey from component is string | null. Payload otpkey is string | null.
      otpkey: data.otpKey
    };
  }

  fromApiPayload(payload: any): YubikeyEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as YubikeyEnrollmentData;
  }
}
