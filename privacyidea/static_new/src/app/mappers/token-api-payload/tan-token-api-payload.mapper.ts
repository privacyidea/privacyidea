import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface TanEnrollmentData extends TokenEnrollmentData {
  type: "tan";
  tanCount?: number;
  tanLength?: number;
}

export interface TanEnrollmentPayload extends TokenEnrollmentPayload {
  tancount?: number;
  tanlength?: number;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class TanApiPayloadMapper implements TokenApiPayloadMapper<TanEnrollmentData> {
  toApiPayload(data: TanEnrollmentData): TanEnrollmentPayload {
    const payload: TanEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      tancount: data.tanCount,
      tanlength: data.tanLength,
      serial: data.serial ?? null
    };
    if (payload.tancount === undefined) delete payload.tancount;
    if (payload.tanlength === undefined) delete payload.tanlength;
    if (payload.serial === null) delete payload.serial;
    return payload;
  }

  fromApiPayload(payload: any): TanEnrollmentData {
    return {
      ...payload,
      tanCount: payload.tancount,
      tanLength: payload.tanlength
    } as TanEnrollmentData;
  }
}
