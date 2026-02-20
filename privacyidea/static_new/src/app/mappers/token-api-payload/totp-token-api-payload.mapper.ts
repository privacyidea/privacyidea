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

export interface TotpEnrollmentData extends TokenEnrollmentData {
  type: "totp";
  generateOnServer?: boolean;
  otpKey?: string;
  otpLength?: number;
  hashAlgorithm?: string;
  timeStep?: number;
}

export interface TotpEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  otplen?: number;
  hashlib?: string;
  timeStep?: number;
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class TotpApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<TotpEnrollmentData> {

  override toApiPayload(data: TotpEnrollmentData): TotpEnrollmentPayload {
    const basePayload = super.toApiPayload(data);
    const payload: TotpEnrollmentPayload = {
      ...basePayload,
      otpkey: data.generateOnServer ? null : (data.otpKey ?? null),
      genkey: data.generateOnServer ? 1 : 0,
      ...(data.otpLength !== undefined && { otplen: Number(data.otpLength) }),
      ...(data.hashAlgorithm !== undefined && { hashlib: data.hashAlgorithm }),
      ...(data.timeStep !== undefined && { timeStep: Number(data.timeStep) })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): TotpEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as TotpEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): TotpEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "totp",
      otpLength: details.otplen ? Number(details.otplen) : undefined,
      hashAlgorithm: details.info?.hashlib ?? undefined,
      timeStep: details.info?.timeStep !== undefined ? Number(details.info.timeStep) : undefined
    };
  }
}
