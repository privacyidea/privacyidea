import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Yubico Cloud-specific enrollment data
export interface YubicoEnrollmentData extends TokenEnrollmentData {
  type: 'yubico';
  yubicoIdentifier?: string; // This will be mapped to 'yubico.tokenid' in toApiPayload
}

export interface YubicoEnrollmentPayload extends TokenEnrollmentPayload {
  'yubico.tokenid'?: string;
}

@Injectable({ providedIn: 'root' })
export class YubicoApiPayloadMapper
  implements TokenApiPayloadMapper<YubicoEnrollmentData>
{
  toApiPayload(data: YubicoEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): YubicoEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as YubicoEnrollmentData;
  }
}
