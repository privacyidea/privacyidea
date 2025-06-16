import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Certificate Token-specific enrollment data
export interface CertificateEnrollmentData extends TokenEnrollmentData {
  type: 'certificate';
  caConnector?: string;
  certTemplate?: string;
  pem?: string;
  // genkey=1 is hardcoded in TokenService
}

export interface CertificateEnrollmentPayload extends TokenEnrollmentPayload {
  genkey: 1;
  ca?: string;
  template?: string;
  pem?: string;
}

@Injectable({ providedIn: 'root' })
export class CertificateApiPayloadMapper
  implements TokenApiPayloadMapper<CertificateEnrollmentData>
{
  toApiPayload(data: CertificateEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): CertificateEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as CertificateEnrollmentData;
  }
}
