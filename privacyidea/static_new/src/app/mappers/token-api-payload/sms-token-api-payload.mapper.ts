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
import { parseBooleanValue } from "../../utils/parse-boolean-value";

export interface SmsEnrollmentData extends TokenEnrollmentData {
  type: "sms";
  smsGateway?: string;
  phoneNumber?: string;
  readNumberDynamically?: boolean;
}

export interface SmsEnrollmentPayload extends TokenEnrollmentPayload {
  "sms.identifier"?: string;
  phone: string | null;
  dynamic_phone?: boolean;
}

@Injectable({ providedIn: "root" })
export class SmsApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<SmsEnrollmentData> {

  override toApiPayload(data: SmsEnrollmentData): SmsEnrollmentPayload {
    const payload: SmsEnrollmentPayload = {
      ...super.toApiPayload(data),
      ...(data.smsGateway != null && { "sms.identifier": data.smsGateway }),
      phone: data.readNumberDynamically ? "" : (data.phoneNumber ?? ""),
      dynamic_phone: data.readNumberDynamically ?? false
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): SmsEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as SmsEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): SmsEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "sms",
      smsGateway: details.info?.["sms.identifier"] ?? undefined,
      phoneNumber: details.info?.phone ?? "",
      readNumberDynamically: parseBooleanValue(details.info?.dynamic_phone ?? false)
    };
  }
}
