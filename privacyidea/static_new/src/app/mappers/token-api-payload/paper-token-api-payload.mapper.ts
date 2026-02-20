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

export interface PaperEnrollmentData extends TokenEnrollmentData {
  type: "paper";
  otpLength?: number;
  otpCount?: number;
}

export interface PaperEnrollmentPayload extends TokenEnrollmentPayload {
  otplen?: number;
  otpcount?: number;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class PaperApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<PaperEnrollmentData> {

  override toApiPayload(data: PaperEnrollmentData): PaperEnrollmentPayload {
    const basePayload = super.toApiPayload(data);
    const payload: PaperEnrollmentPayload = {
      ...basePayload,
      ...(data.otpLength !== undefined && { otplen: data.otpLength }),
      ...(data.otpCount !== undefined && { otpcount: data.otpCount })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): PaperEnrollmentData {
    return {
      ...payload,
      otpLength: payload.otplen,
      otpCount: payload.otpcount
    } as PaperEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): PaperEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "paper",
      otpLength: details.otplen !== undefined ? Number(details.otplen) : undefined
    };
  }
}
