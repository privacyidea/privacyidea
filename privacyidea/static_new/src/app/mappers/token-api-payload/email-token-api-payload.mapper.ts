import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface EmailEnrollmentData extends TokenEnrollmentData {
  type: "email";
  emailAddress?: string;
  readEmailDynamically?: boolean;
}

export interface EmailEnrollmentPayload extends TokenEnrollmentPayload {
  email?: string;
  dynamic_email: boolean;
}

@Injectable({ providedIn: "root" })
export class EmailApiPayloadMapper implements TokenApiPayloadMapper<EmailEnrollmentData> {
  toApiPayload(data: EmailEnrollmentData): EmailEnrollmentPayload {
    const payload: EmailEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user? data.realm : null,
      pin: data.pin,
      email: data.emailAddress,
      dynamic_email: !!data.readEmailDynamically
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.email === undefined) {
      delete payload.email;
    }
    return payload;
  }

  fromApiPayload(payload: any): EmailEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as EmailEnrollmentData;
  }
}
