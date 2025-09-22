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
import { TokenApiPayloadMapper, TokenEnrollmentData, TokenEnrollmentPayload } from "./_token-api-payload.mapper";

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
export class SmsApiPayloadMapper implements TokenApiPayloadMapper<SmsEnrollmentData> {
  toApiPayload(data: SmsEnrollmentData): SmsEnrollmentPayload {
    const payload: SmsEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      "sms.identifier": data.smsGateway,
      phone: data.readNumberDynamically ? null : (data.phoneNumber ?? null),
      dynamic_phone: data.readNumberDynamically
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload["sms.identifier"] === undefined) {
      delete payload["sms.identifier"];
    }
    if (payload.dynamic_phone === undefined) {
      delete payload.dynamic_phone;
    }
    return payload;
  }

  fromApiPayload(payload: any): SmsEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as SmsEnrollmentData;
  }
}
