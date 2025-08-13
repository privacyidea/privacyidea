import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
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
    return {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      genkey: 1
    };
  }

  fromApiPayload(payload: any): PushEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as PushEnrollmentData;
  }
}
