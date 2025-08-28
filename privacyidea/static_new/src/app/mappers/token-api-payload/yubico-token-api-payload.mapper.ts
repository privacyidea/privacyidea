import { Injectable } from "@angular/core";
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

export interface YubicoEnrollmentData extends TokenEnrollmentData {
  type: "yubico";
  yubicoIdentifier?: string;
}

export interface YubicoEnrollmentPayload extends TokenEnrollmentPayload {
  "yubico.tokenid"?: string;
}

@Injectable({ providedIn: "root" })
export class YubicoApiPayloadMapper implements TokenApiPayloadMapper<YubicoEnrollmentData> {
  toApiPayload(data: YubicoEnrollmentData): YubicoEnrollmentPayload {
    const payload: YubicoEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      "yubico.tokenid": data.yubicoIdentifier
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload["yubico.tokenid"] === undefined) {
      delete payload["yubico.tokenid"];
    }
    return payload;
  }

  fromApiPayload(payload: any): YubicoEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as YubicoEnrollmentData;
  }
}
