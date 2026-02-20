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

export interface VascoEnrollmentData extends TokenEnrollmentData {
  type: "vasco";
  useVascoSerial?: boolean;
  vascoSerial?: string;
  otpKey?: string;
}

export interface VascoEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey?: string;
  genkey: 0;
}

@Injectable({ providedIn: "root" })
export class VascoApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<VascoEnrollmentData> {

  override toApiPayload(data: VascoEnrollmentData): VascoEnrollmentPayload {
    // Get base payload and remove serial if it is null
    const basePayload = super.toApiPayload(data);
    const payload: VascoEnrollmentPayload = {
      ...basePayload,
      genkey: 0,
      ...(data.otpKey != null && { otpkey: data.otpKey }),
      ...(data.useVascoSerial && data.vascoSerial != null && { serial: data.vascoSerial })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): VascoEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as VascoEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: any): VascoEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "vasco"
    };
  }
}
