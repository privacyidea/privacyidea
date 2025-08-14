import { RemoteServer } from "../../services/privavyidea-server/privacyidea-server.service";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";

export interface RemoteEnrollmentData extends TokenEnrollmentData {
  type: "remote";
  remoteServer: RemoteServer | null;
  remoteSerial: string;
  remoteUser: string;
  remoteRealm: string;
  remoteResolver: string;
  checkPinLocally: boolean;
}

export interface RemoteEnrollmentPayload extends TokenEnrollmentPayload {
  "remote.server_id": string | null;
  "remote.serial": string;
  "remote.user": string;
  "remote.realm": string;
  "remote.resolver": string;
  "remote.local_checkpin": boolean;
}

@Injectable({ providedIn: "root" })
export class RemoteApiPayloadMapper implements TokenApiPayloadMapper<RemoteEnrollmentData> {
  toApiPayload(data: RemoteEnrollmentData): RemoteEnrollmentPayload {
    return {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      pin: data.pin,
      "remote.server_id": data.remoteServer?.id ?? null,
      "remote.serial": data.remoteSerial,
      "remote.user": data.remoteUser,
      "remote.realm": data.remoteRealm,
      "remote.resolver": data.remoteResolver,
      "remote.local_checkpin": data.checkPinLocally
    };
  }

  fromApiPayload(payload: any): RemoteEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RemoteEnrollmentData;
  }
}
