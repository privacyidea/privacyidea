import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';
import { Injectable } from '@angular/core';

// Interface for SSHKey-specific enrollment data
export interface SshkeyEnrollmentData extends TokenEnrollmentData {
  type: 'sshkey';
  sshPublicKey?: string; // Corresponds to 'sshkey' in API payload (from TokenService)
}

export interface SshkeyEnrollmentPayload extends TokenEnrollmentPayload {
  sshkey?: string;
}

@Injectable({ providedIn: 'root' })
export class SshkeyApiPayloadMapper
  implements TokenApiPayloadMapper<SshkeyEnrollmentData>
{
  toApiPayload(data: SshkeyEnrollmentData): any {
    // Placeholder: Implement transformation to API payload.
    return { ...data, sshkey: data.sshPublicKey };
  }

  fromApiPayload(payload: any): SshkeyEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return { ...payload, sshPublicKey: payload.sshkey } as SshkeyEnrollmentData;
  }
}
