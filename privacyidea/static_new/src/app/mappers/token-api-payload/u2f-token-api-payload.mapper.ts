import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface U2fEnrollmentData extends TokenEnrollmentData {
  type: "u2f";
}

export interface U2fEnrollmentPayload extends TokenEnrollmentPayload {
}

@Injectable({ providedIn: "root" })
export class U2fApiPayloadMapper implements TokenApiPayloadMapper<U2fEnrollmentData> {
  toApiPayload(data: U2fEnrollmentData): U2fEnrollmentPayload {
    const payload: U2fEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    return payload;
  }

  fromApiPayload(payload: any): U2fEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as U2fEnrollmentData;
  }
}
