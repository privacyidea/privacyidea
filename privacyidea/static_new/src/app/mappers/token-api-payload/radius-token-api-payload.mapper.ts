import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for RADIUS-specific enrollment data
export interface RadiusEnrollmentData extends TokenEnrollmentData {
  type: 'radius';
  radiusServerConfiguration?: string; // Mapped to 'radius.identifier'
  radiusUser?: string; // Mapped to 'radius.user'
}

export interface RadiusEnrollmentPayload extends TokenEnrollmentPayload {
  'radius.identifier'?: string;
  'radius.user'?: string;
}

@Injectable({ providedIn: 'root' })
export class RadiusApiPayloadMapper
  implements TokenApiPayloadMapper<RadiusEnrollmentData>
{
  toApiPayload(data: RadiusEnrollmentData): RadiusEnrollmentPayload {
    const payload: RadiusEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      'radius.identifier': data.radiusServerConfiguration,
      'radius.user': data.radiusUser,
    };

    if (payload['radius.identifier'] === undefined) {
      delete payload['radius.identifier'];
    }
    if (payload['radius.user'] === undefined) {
      delete payload['radius.user'];
    }
    return payload;
  }

  fromApiPayload(payload: any): RadiusEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RadiusEnrollmentData;
  }
}
