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
  toApiPayload(data: CertificateEnrollmentData): CertificateEnrollmentPayload {
    const payload: CertificateEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      genkey: 1, // As per switch statement
      ca: data.caConnector,
      template: data.certTemplate,
      pem: data.pem,
    };

    if (payload.ca === undefined) delete payload.ca;
    if (payload.template === undefined) delete payload.template;
    if (payload.pem === undefined) delete payload.pem;

    return payload;
  }

  fromApiPayload(payload: any): CertificateEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as CertificateEnrollmentData;
  }
}
