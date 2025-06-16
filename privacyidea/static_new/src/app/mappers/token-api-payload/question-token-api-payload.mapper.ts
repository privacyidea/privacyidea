import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Question Token-specific enrollment data
export interface QuestionEnrollmentData extends TokenEnrollmentData {
  type: 'question';
  answers?: Record<string, string>; // Mapped to 'questions' in payload
}

export interface QuestionEnrollmentPayload extends TokenEnrollmentPayload {
  questions?: Record<string, string>;
}

@Injectable({ providedIn: 'root' })
export class QuestionApiPayloadMapper
  implements TokenApiPayloadMapper<QuestionEnrollmentData>
{
  toApiPayload(data: QuestionEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): QuestionEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as QuestionEnrollmentData;
  }
}
