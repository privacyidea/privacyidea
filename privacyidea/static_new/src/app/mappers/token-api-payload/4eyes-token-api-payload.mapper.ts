import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for 4Eyes Token-specific enrollment data
export interface FourEyesEnrollmentData extends TokenEnrollmentData {
  type: '4eyes';
  separator?: string;
  requiredTokenOfRealms?: {
    realm: string;
    tokens: number;
  }[]; // Mapped to '4eyes' object in payload
  onlyAddToRealm?: boolean;
  userRealm?: string; // Used if onlyAddToRealm is true
}

@Injectable({ providedIn: 'root' })
export class FourEyesApiPayloadMapper
  implements TokenApiPayloadMapper<FourEyesEnrollmentData>
{
  toApiPayload(data: FourEyesEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): FourEyesEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as FourEyesEnrollmentData;
  }
}
