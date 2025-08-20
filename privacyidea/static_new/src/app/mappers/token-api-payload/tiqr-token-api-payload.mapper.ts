import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface TiqrEnrollmentData extends TokenEnrollmentData {
  type: "tiqr";
}

export interface TiqrEnrollmentPayload extends TokenEnrollmentPayload {
}

@Injectable({ providedIn: "root" })
export class TiqrApiPayloadMapper implements TokenApiPayloadMapper<TiqrEnrollmentData> {
  toApiPayload(data: TiqrEnrollmentData): TiqrEnrollmentPayload {
    return {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin
    };
  }

  fromApiPayload(payload: any): TiqrEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as TiqrEnrollmentData;
  }
}
