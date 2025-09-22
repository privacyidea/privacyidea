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
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

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
      realm: data.user ? data.realm : null,
      pin: data.pin,
      sshkey: data.sshPublicKey
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.sshkey === undefined) delete payload.sshkey;
    return payload;
  }

  fromApiPayload(payload: any): SshkeyEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return { ...payload, sshPublicKey: payload.sshkey } as SshkeyEnrollmentData;
  }
}
