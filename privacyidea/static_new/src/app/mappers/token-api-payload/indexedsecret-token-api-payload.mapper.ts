import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Indexed Secret-specific enrollment data
export interface IndexedSecretEnrollmentData extends TokenEnrollmentData {
  type: 'indexedsecret';
  otpKey?: string;
}

export interface IndexedSecretEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey?: string;
}

@Injectable({ providedIn: 'root' })
export class IndexedSecretApiPayloadMapper
  implements TokenApiPayloadMapper<IndexedSecretEnrollmentData>
{
  toApiPayload(data: IndexedSecretEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): IndexedSecretEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as IndexedSecretEnrollmentData;
  }
}
