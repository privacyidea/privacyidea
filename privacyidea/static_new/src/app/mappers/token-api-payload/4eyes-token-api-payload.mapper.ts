import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface FourEyesEnrollmentData extends TokenEnrollmentData {
  type: "4eyes";
  separator: string;
  requiredTokenOfRealms: {
    realm: string;
    tokens: number;
  }[];
  onlyAddToRealm: boolean;
  userRealm?: string;
}

export interface FourEyesEnrollmentPayload extends TokenEnrollmentPayload {
  separator: string;
  "4eyes": { [key: string]: { count: number; selected: boolean } };
  realm?: string;
}

@Injectable({ providedIn: "root" })
export class FourEyesApiPayloadMapper implements TokenApiPayloadMapper<FourEyesEnrollmentData> {
  toApiPayload(data: FourEyesEnrollmentData): FourEyesEnrollmentPayload {
    const payload: FourEyesEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      pin: data.pin,
      user: data.user,
      separator: data.separator,
      "4eyes": (data.requiredTokenOfRealms ?? []).reduce(
        (acc: { [key: string]: { count: number; selected: boolean } }, curr) => {
          acc[curr.realm] = { count: curr.tokens, selected: true };
          return acc;
        },
        {}
      )
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.userRealm;
      payload.user = null;
    }
    return payload;
  }

  fromApiPayload(payload: any): FourEyesEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as FourEyesEnrollmentData;
  }
}
