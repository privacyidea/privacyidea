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

export interface U2fEnrollmentData extends TokenEnrollmentData {
  type: "u2f";
}

export interface U2fEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: "root" })
export class U2fApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<U2fEnrollmentData> {

  override toApiPayload(data: U2fEnrollmentData): U2fEnrollmentPayload {
    const payload: U2fEnrollmentPayload = super.toApiPayload(data);

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): U2fEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as U2fEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): U2fEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "u2f"
    };
  }
}
