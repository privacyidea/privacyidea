import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface MotpEnrollmentData extends TokenEnrollmentData {
  type: "motp";
  generateOnServer?: boolean;
  otpKey?: string;
  motpPin?: string;
}

export interface MotpEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  motppin?: string;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class MotpApiPayloadMapper implements TokenApiPayloadMapper<MotpEnrollmentData> {
  toApiPayload(data: MotpEnrollmentData): MotpEnrollmentPayload {
    const payload: MotpEnrollmentPayload = {
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
      motppin: data.motpPin,
      serial: data.serial ?? null
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.motppin === undefined) delete payload.motppin;
    if (payload.serial === null) delete payload.serial;
    return payload;
  }

  fromApiPayload(payload: any): MotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as MotpEnrollmentData;
  }
}
