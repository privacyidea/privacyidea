import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface SshkeyEnrollmentData extends TokenEnrollmentData {
  type: "sshkey";
  sshPublicKey?: string;
}

export interface SshkeyEnrollmentPayload extends TokenEnrollmentPayload {
  sshkey?: string;
}

@Injectable({ providedIn: "root" })
export class SshkeyApiPayloadMapper implements TokenApiPayloadMapper<SshkeyEnrollmentData> {
  toApiPayload(data: SshkeyEnrollmentData): SshkeyEnrollmentPayload {
    // 'sshkey' type is not in the main switch statement.
    // Mapping based on defined interfaces and component behavior.
    const payload: SshkeyEnrollmentPayload = {
      type: data.type,
      description: data.description, // EnrollSshkeyComponent updates description
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      sshkey: data.sshPublicKey
    };

    if (payload.sshkey === undefined) delete payload.sshkey;
    return payload;
  }

  fromApiPayload(payload: any): SshkeyEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return { ...payload, sshPublicKey: payload.sshkey } as SshkeyEnrollmentData;
  }
}
