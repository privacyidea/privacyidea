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
export class TanApiPayloadMapper implements TokenApiPayloadMapper<TanEnrollmentData> {
  toApiPayload(data: TanEnrollmentData): TanEnrollmentPayload {
    const payload: TanEnrollmentPayload = {
      type: data.type,
      description: data.description,
      container_serial: data.containerSerial,
      validity_period_start: data.validityPeriodStart,
      validity_period_end: data.validityPeriodEnd,
      user: data.user,
      realm: data.user ? data.realm : null,
      pin: data.pin,
      tancount: data.tanCount,
      tanlength: data.tanLength,
      serial: data.serial ?? null
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.tancount === undefined) delete payload.tancount;
    if (payload.tanlength === undefined) delete payload.tanlength;
    if (payload.serial === null) delete payload.serial;
    return payload;
  }

  fromApiPayload(payload: any): TanEnrollmentData {
    return {
      ...payload,
      tanCount: payload.tancount,
      tanLength: payload.tanlength
    } as TanEnrollmentData;
  }
}
