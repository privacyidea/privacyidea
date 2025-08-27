import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface RadiusEnrollmentData extends TokenEnrollmentData {
  type: "radius";
  radiusServerConfiguration?: string;
  radiusUser?: string;
}

export interface RadiusEnrollmentPayload extends TokenEnrollmentPayload {
  "radius.identifier"?: string;
  "radius.user"?: string;
}

@Injectable({ providedIn: "root" })
export class RadiusApiPayloadMapper implements TokenApiPayloadMapper<RadiusEnrollmentData> {
  toApiPayload(data: RadiusEnrollmentData): RadiusEnrollmentPayload {
    const payload: RadiusEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      "radius.identifier": data.radiusServerConfiguration,
      "radius.user": data.radiusUser
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload["radius.identifier"] === undefined) {
      delete payload["radius.identifier"];
    }
    if (payload["radius.user"] === undefined) {
      delete payload["radius.user"];
    }
    return payload;
  }

  fromApiPayload(payload: any): RadiusEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RadiusEnrollmentData;
  }
}
