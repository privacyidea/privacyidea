import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

// Interface for Question Token-specific enrollment data
export interface QuestionEnrollmentData extends TokenEnrollmentData {
  type: "question";
  answers?: Record<string, string>; // Mapped to 'questions' in payload
}

export interface QuestionEnrollmentPayload extends TokenEnrollmentPayload {
  questions?: Record<string, string>;
}

@Injectable({ providedIn: "root" })
export class QuestionApiPayloadMapper implements TokenApiPayloadMapper<QuestionEnrollmentData> {
  toApiPayload(data: QuestionEnrollmentData): QuestionEnrollmentPayload {
    const payload: QuestionEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      questions: data.answers
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.questions === undefined) {
      delete payload.questions;
    }
    return payload;
  }

  fromApiPayload(payload: any): QuestionEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as QuestionEnrollmentData;
  }
}
