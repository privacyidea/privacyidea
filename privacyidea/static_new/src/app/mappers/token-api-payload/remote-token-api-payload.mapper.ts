import { RemoteServer } from '../../services/privavyidea-server/privacyidea-server.service';
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for Remote Token-specific enrollment data
export interface RemoteEnrollmentData extends TokenEnrollmentData {
  type: 'remote';
  remoteServer: RemoteServer | null;
  remoteSerial: string;
  remoteUser: string;
  remoteRealm: string;
  remoteResolver: string; // Keep original type
  checkPinLocally: boolean;
}

@Injectable({ providedIn: 'root' })
export class RemoteApiPayloadMapper
  implements TokenApiPayloadMapper<RemoteEnrollmentData>
{
  toApiPayload(data: RemoteEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): RemoteEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RemoteEnrollmentData;
  }
}
