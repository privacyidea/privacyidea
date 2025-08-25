import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for Application Specific Password enrollment data
export interface ApplspecEnrollmentData extends TokenEnrollmentData {
  type: "applspec";
  generateOnServer?: boolean;
  otpKey?: string;
  serviceId?: string;
}

export interface ApplspecEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  service_id?: string;
}

@Injectable({ providedIn: "root" })
export class ApplspecApiPayloadMapper implements TokenApiPayloadMapper<ApplspecEnrollmentData> {
  toApiPayload(data: ApplspecEnrollmentData): ApplspecEnrollmentPayload {
    const payload: ApplspecEnrollmentPayload = {
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
      service_id: data.serviceId
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    if (payload.service_id === undefined) {
      delete payload.service_id;
    }
    return payload;
  }

  fromApiPayload(payload: any): ApplspecEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as ApplspecEnrollmentData;
  }
}
