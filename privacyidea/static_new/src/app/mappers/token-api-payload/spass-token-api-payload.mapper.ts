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

export interface SpassEnrollmentData extends TokenEnrollmentData {
  type: "spass";
}

export interface SpassEnrollmentPayload extends TokenEnrollmentPayload {}

@Injectable({ providedIn: "root" })
export class SpassApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<SpassEnrollmentData> {

  override toApiPayload(data: SpassEnrollmentData): SpassEnrollmentPayload {
    const payload: SpassEnrollmentPayload = super.toApiPayload(data);

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    return payload;
  }

  override fromApiPayload(payload: any): SpassEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as SpassEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): SpassEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "spass"
    };
  }
}
