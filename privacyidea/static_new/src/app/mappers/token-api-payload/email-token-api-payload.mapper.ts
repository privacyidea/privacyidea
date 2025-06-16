import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Email Token-specific enrollment data
export interface EmailEnrollmentData extends TokenEnrollmentData {
  type: 'email';
  emailAddress?: string;
  readEmailDynamically?: boolean;
}

@Injectable({ providedIn: 'root' })
export class EmailApiPayloadMapper
  implements TokenApiPayloadMapper<EmailEnrollmentData>
{
  toApiPayload(data: EmailEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): EmailEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as EmailEnrollmentData;
  }
}
