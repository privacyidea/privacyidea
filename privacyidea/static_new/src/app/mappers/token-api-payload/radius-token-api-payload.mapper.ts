import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for RADIUS-specific enrollment data
export interface RadiusEnrollmentData extends TokenEnrollmentData {
  type: 'radius';
  radiusServerConfiguration?: string; // Mapped to 'radius.identifier'
  radiusUser?: string; // Mapped to 'radius.user'
}

@Injectable({ providedIn: 'root' })
export class RadiusApiPayloadMapper
  implements TokenApiPayloadMapper<RadiusEnrollmentData>
{
  toApiPayload(data: RadiusEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): RadiusEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RadiusEnrollmentData;
  }
}
