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

// Interface for DayPassword-specific enrollment data
export interface DaypasswordEnrollmentData extends TokenEnrollmentData {
  type: "daypassword";
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
  timeStep?: string;
  generateOnServer?: boolean; // This is from component options, influences otpKey
}

export interface DaypasswordEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey?: string; // Set if generateOnServer is false
  otplen?: number;
  hashlib?: string;
  timeStep?: string;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class DaypasswordApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<DaypasswordEnrollmentData> {

  override toApiPayload(data: DaypasswordEnrollmentData): DaypasswordEnrollmentPayload {
    const payload: DaypasswordEnrollmentPayload = {
      ...super.toApiPayload(data),
      // otpKey is set based on component logic:
      // if generateOnServer is true, data.otpKey is undefined.
      // if generateOnServer is false, data.otpKey is the key.
      ...(data.otpKey != null && { otpkey: data.otpKey }),
      ...(data.otpLength != null && { otplen: Number(data.otpLength) }),
      ...(data.hashAlgorithm != null && { hashlib: data.hashAlgorithm }),
      ...(data.timeStep != null && { timeStep: data.timeStep })
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): DaypasswordEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as DaypasswordEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): DaypasswordEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "daypassword",
      otpLength: details.otplen !== undefined ? Number(details.otplen) : undefined,
      hashAlgorithm: details.info?.hashlib ?? undefined,
      timeStep: details.info?.timeStep !== undefined ? details.info.timeStep : undefined
    };
  }
}
