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
import {
  BaseApiPayloadMapper,
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { TokenDetails } from "../../services/token/token.service";

export interface SshkeyEnrollmentData extends TokenEnrollmentData {
  type: "sshkey";
  sshPublicKey?: string;
}

export interface SshkeyEnrollmentPayload extends TokenEnrollmentPayload {
  sshkey?: string;
}

@Injectable({ providedIn: "root" })
export class SshkeyApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<SshkeyEnrollmentData> {

  override toApiPayload(data: SshkeyEnrollmentData): SshkeyEnrollmentPayload {
    const basePayload = super.toApiPayload(data);
    const payload: SshkeyEnrollmentPayload = {
      ...basePayload,
      ...(data.sshPublicKey !== undefined && { sshkey: data.sshPublicKey })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): SshkeyEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return { ...payload, sshPublicKey: payload.sshkey } as SshkeyEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): SshkeyEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "sshkey"
    };
  }
}
