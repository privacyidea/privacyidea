import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for 4Eyes Token-specific enrollment data
export interface FourEyesEnrollmentData extends TokenEnrollmentData {
  type: '4eyes'; // type is part of TokenEnrollmentData
  separator: string;
  requiredTokenOfRealms: {
    realm: string;
    tokens: number;
  }[];
  onlyAddToRealm: boolean;
  userRealm?: string; // Used if onlyAddToRealm is true
}

export interface FourEyesEnrollmentPayload extends TokenEnrollmentPayload {
  separator: string;
  '4eyes': { [key: string]: { count: number; selected: boolean } };
  realm?: string; // Conditionally set if onlyAddToRealm is true
  // user property is inherited from TokenEnrollmentPayload and can be string | null
}

@Injectable({ providedIn: 'root' })
export class FourEyesApiPayloadMapper
  implements TokenApiPayloadMapper<FourEyesEnrollmentData>
{
  toApiPayload(data: FourEyesEnrollmentData): FourEyesEnrollmentPayload {
    const payload: FourEyesEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      pin: data.pin,
      user: data.user, // Initially set user from data
      separator: data.separator,
      '4eyes': (data.requiredTokenOfRealms ?? []).reduce(
        (
          acc: { [key: string]: { count: number; selected: boolean } },
          curr,
        ) => {
          acc[curr.realm] = { count: curr.tokens, selected: true };
          return acc;
        },
        {},
      ),
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.userRealm;
      payload.user = null; // Override user to null as per switch logic
    }
    return payload;
  }

  fromApiPayload(payload: any): FourEyesEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as FourEyesEnrollmentData;
  }
}
