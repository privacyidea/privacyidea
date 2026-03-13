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
import {
  BaseApiPayloadMapper,
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";
import { Injectable } from "@angular/core";
import { TokenDetails } from "../../services/token/token.service";

// Interface for Application Specific Password enrollment data
export interface ApplspecEnrollmentData extends TokenEnrollmentData {
  type: "applspec";
  generateOnServer?: boolean;
  otpKey?: string;
  serviceId?: string;
}

export interface ApplspecEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  genkey: 0 | 1;
  service_id?: string;
}

@Injectable({ providedIn: "root" })
export class ApplspecApiPayloadMapper
  extends BaseApiPayloadMapper
  implements TokenApiPayloadMapper<ApplspecEnrollmentData>
{
  override toApiPayload(data: ApplspecEnrollmentData): ApplspecEnrollmentPayload {
    const payload: ApplspecEnrollmentPayload = {
      ...super.toApiPayload(data),
      otpkey: data.generateOnServer ? null : (data.otpKey ?? null),
      genkey: data.generateOnServer ? 1 : 0,
      ...(data.serviceId != null && { service_id: data.serviceId })
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      delete payload.user;
    }

    return payload;
  }

  override fromApiPayload(payload: ApplspecEnrollmentPayload): ApplspecEnrollmentData {
    const baseData = super.fromApiPayload(payload);
    return {
      ...baseData,
      type: "applspec",
      generateOnServer: payload.genkey === 1,
      otpKey: payload.otpkey ?? undefined,
      serviceId: payload.service_id ?? undefined
    };
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): ApplspecEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "applspec",
      ...(details.info?.service_id != null && { serviceId: details.info?.service_id })
    };
  }
}
