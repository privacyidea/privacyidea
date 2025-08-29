import { Injectable } from "@angular/core";
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

export interface TiqrEnrollmentData extends TokenEnrollmentData {
  type: "tiqr";
}

export interface TiqrEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: "root" })
export class TiqrApiPayloadMapper implements TokenApiPayloadMapper<TiqrEnrollmentData> {
  toApiPayload(data: TiqrEnrollmentData): TiqrEnrollmentPayload {
    const payload: TiqrEnrollmentPayload = {
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

  fromApiPayload(payload: any): TiqrEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as TiqrEnrollmentData;
  }
}
