import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for Indexed Secret-specific enrollment data
export interface IndexedSecretEnrollmentData extends TokenEnrollmentData {
  type: "indexedsecret";
  otpKey?: string;
}

export interface IndexedSecretEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey?: string;
}

@Injectable({ providedIn: "root" })
export class IndexedSecretApiPayloadMapper
  implements TokenApiPayloadMapper<IndexedSecretEnrollmentData> {
  toApiPayload(data: IndexedSecretEnrollmentData): IndexedSecretEnrollmentPayload {
    const payload: IndexedSecretEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user? data.realm : null,
      pin: data.pin,
      otpkey: data.otpKey
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.otpkey === undefined) {
      delete payload.otpkey;
    }
    return payload;
  }

  fromApiPayload(payload: any): IndexedSecretEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as IndexedSecretEnrollmentData;
  }
}
