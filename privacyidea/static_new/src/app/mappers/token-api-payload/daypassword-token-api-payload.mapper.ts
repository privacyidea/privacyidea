import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for DayPassword-specific enrollment data
export interface DaypasswordEnrollmentData extends TokenEnrollmentData {
  type: "daypassword";
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
  timeStep?: number; // from component this is number | string
  generateOnServer?: boolean; // This is from component options, influences otpKey
}

export interface DaypasswordEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey?: string; // Set if generateOnServer is false
  otplen?: number;
  hashlib?: string;
  timeStep?: number;
}

@Injectable({ providedIn: "root" })
export class DaypasswordApiPayloadMapper
  implements TokenApiPayloadMapper<DaypasswordEnrollmentData> {
  toApiPayload(data: DaypasswordEnrollmentData): DaypasswordEnrollmentPayload {
    const payload: DaypasswordEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user? data.realm : null,
      pin: data.pin,
      // otpKey is set based on component logic:
      // if generateOnServer is true, data.otpKey is undefined.
      // if generateOnServer is false, data.otpKey is the key.
      otpkey: data.otpKey,
      otplen: data.otpLength !== undefined ? Number(data.otpLength) : undefined,
      hashlib: data.hashAlgorithm,
      timeStep: data.timeStep !== undefined ? Number(data.timeStep) : undefined
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.otpkey === undefined) delete payload.otpkey;
    if (payload.otplen === undefined) delete payload.otplen;
    if (payload.hashlib === undefined) delete payload.hashlib;
    if (payload.timeStep === undefined) delete payload.timeStep;
    return payload;
  }

  fromApiPayload(payload: any): DaypasswordEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as DaypasswordEnrollmentData;
  }
}
