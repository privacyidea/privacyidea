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
import { RemoteServer } from "../../services/privavyidea-server/privacyidea-server.service";
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

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
    const payload: RemoteEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
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

  fromApiPayload(payload: any): RemoteEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RemoteEnrollmentData;
  }
}
