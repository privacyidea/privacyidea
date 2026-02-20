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

export interface TanEnrollmentData extends TokenEnrollmentData {
  type: "tan";
  tanCount?: number;
  tanLength?: number;
}

export interface TanEnrollmentPayload extends TokenEnrollmentPayload {
  tancount?: number;
  tanlength?: number;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class TanApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<TanEnrollmentData> {

  override toApiPayload(data: TanEnrollmentData): TanEnrollmentPayload {
    const payload: TanEnrollmentPayload = {
      ...super.toApiPayload(data),
      ...(data.tanCount != null && { tancount: data.tanCount }),
      ...(data.tanLength != null && { tanlength: data.tanLength })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): TanEnrollmentData {
    return {
      ...payload,
      tanCount: payload.tancount,
      tanLength: payload.tanlength
    } as TanEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): TanEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "tan",
      tanCount: details.info?.["tan.count"] ?? undefined
    };
  }
}
