/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { Injectable } from "@angular/core";
import { RemoteServer } from "../../services/privacyidea-server/privacyidea-server.service";
import {
  BaseApiPayloadMapper,
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { TokenDetails } from "../../services/token/token.service";
import { parseBooleanValue } from "../../utils/parse-boolean-value";

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
export class RemoteApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<RemoteEnrollmentData> {

  override toApiPayload(data: RemoteEnrollmentData): RemoteEnrollmentPayload {
    const payload: RemoteEnrollmentPayload = {
      ...super.toApiPayload(data),
      "remote.server_id": data.remoteServer?.id ?? null,
      "remote.serial": data.remoteSerial,
      "remote.user": data.remoteUser,
      "remote.realm": data.remoteRealm,
      "remote.resolver": data.remoteResolver,
      "remote.local_checkpin": data.checkPinLocally
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    return payload;
  }

  override fromApiPayload(payload: any): RemoteEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RemoteEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): RemoteEnrollmentData {
    const enrollData: RemoteEnrollmentData = {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "remote",
      remoteServer: details.info?.["remote.server_id"] ? {id: details.info?.["remote.server_id"]}  as RemoteServer : null,
      remoteSerial: details.info?.["remote.serial"] ?? "",
      remoteUser: details.info?.["remote.user"] ?? "",
      remoteRealm: details.info?.["remote.realm"] ?? "",
      remoteResolver: details.info?.["remote.resolver"] ?? "",
      checkPinLocally: parseBooleanValue(details.info?.["remote.local_checkpin"] ?? false)
    };

    return enrollData;
  }
}
