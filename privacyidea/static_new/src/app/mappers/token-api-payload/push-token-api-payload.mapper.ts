import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface PushEnrollmentData extends TokenEnrollmentData {
  type: "push";
}

export interface PushEnrollmentPayload extends TokenEnrollmentPayload {
  genkey: 1;
}

@Injectable({ providedIn: "root" })
export class PushApiPayloadMapper implements TokenApiPayloadMapper<PushEnrollmentData> {
  toApiPayload(data: PushEnrollmentData): PushEnrollmentPayload {
    const payload: PushEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user? data.realm : null,
      pin: data.pin,
      genkey: 1
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  fromApiPayload(payload: any): PushEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PushEnrollmentData;
  }
}
