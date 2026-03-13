/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

export interface MotpEnrollmentData extends TokenEnrollmentData {
  type: "motp";
  generateOnServer?: boolean;
  otpKey?: string;
  motpPin?: string;
}

export interface MotpEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string;
  genkey: 0 | 1;
  motppin?: string;
  serial?: string;
}

@Injectable({ providedIn: "root" })
export class MotpApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<MotpEnrollmentData> {
  override toApiPayload(data: MotpEnrollmentData): MotpEnrollmentPayload {
    const basePayload = super.toApiPayload(data);
    const payload: MotpEnrollmentPayload = {
      ...basePayload,
      otpkey: data.generateOnServer === true ? "" : (data.otpKey ?? ""),
      genkey: data.generateOnServer ? 1 : 0,
      ...(data.motpPin !== undefined && { motppin: data.motpPin })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      delete payload.user;
    }
    return payload;
  }

  override fromApiPayload(payload: any): MotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as MotpEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): MotpEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "motp"
    };
  }
}
