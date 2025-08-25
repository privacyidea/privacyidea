import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for Registration Token-specific enrollment data
export interface RegistrationEnrollmentData extends TokenEnrollmentData {
  type: "registration";
}

export interface RegistrationEnrollmentPayload extends TokenEnrollmentPayload {
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class RegistrationApiPayloadMapper
  implements TokenApiPayloadMapper<RegistrationEnrollmentData> {
  toApiPayload(data: RegistrationEnrollmentData): RegistrationEnrollmentPayload {
    // No type-specific fields in switch statement for 'registration'
    const payload: RegistrationEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      serial: data.serial ?? null
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.serial === null) delete payload.serial;

    return payload;
  }

  fromApiPayload(payload: any): RegistrationEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as RegistrationEnrollmentData;
  }
}
