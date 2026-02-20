import { Injectable } from "@angular/core";
import { TokenDetails } from "../../services/token/token.service";

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
export interface EnrollmentResponse<D extends EnrollmentResponseDetail = EnrollmentResponseDetail> {
  type: string;
  detail: D;

  [key: string]: any;
}

export interface EnrollmentResponseDetail {
  type: string;
  serial: string;
  rollout_state?: string;
  threadid?: number;
  passkey_registration?: any;
  u2fRegisterRequest?: any;
  pushurl?: EnrollmentUrl;
  googleurl?: EnrollmentUrl;
  otpkey?: EnrollmentUrl;
  motpurl?: EnrollmentUrl;
  tiqrenroll?: EnrollmentUrl;

  [key: string]: any;
}

export interface EnrollmentUrl {
  description: string;
  img: string;
  value: string;
  value_b32?: string;
}

export type TokenEnrollmentData = {
  type: string;
  description?: string;
  containerSerial?: string;
  validityPeriodStart?: string;
  validityPeriodEnd?: string;
  user?: string;
  realm?: string;
  onlyAddToRealm?: boolean;
  pin?: string;
  serial?: string | null;
  rollover?: boolean | null;
  [key: string]: any; // TODO: remove this when all types are defined
};

export interface TokenEnrollmentPayload {
  type: string;
  description?: string;
  container_serial?: string;
  validity_period_start?: string;
  validity_period_end?: string;
  user?: string | null;
  realm?: string | null;
  pin?: string;
  rollover?: boolean | null;
  serial?: string | null;
}

export interface TokenApiPayloadMapper<T> {
  toApiPayload(data: T): any;
  fromApiPayload(data: any): T;
  fromTokenDetailsToEnrollmentData(details: TokenDetails): T;
}

@Injectable({ providedIn: "root" })
export class BaseApiPayloadMapper implements TokenApiPayloadMapper<TokenEnrollmentData> {
  toApiPayload(data: TokenEnrollmentData): TokenEnrollmentPayload {
    // only include defined and non-null properties in the payload for optional fields
    return {
      type: data.type,
      ...(data.description != null && { description: data.description }),
      ...(data.containerSerial != null && { container_serial: data.containerSerial }),
      ...(data.validityPeriodStart != null && { validity_period_start: data.validityPeriodStart }),
      ...(data.validityPeriodEnd != null && { validity_period_end: data.validityPeriodEnd }),
      ...(data.user && { user: data.user }),
      ...(data.realm && data.user && { realm: data.realm }),
      ...(data.pin != null && { pin: data.pin }),
      ...(data.serial != null && { serial: data.serial }),
      ...(data.rollover != null && { rollover: data.rollover })
    };
  }

  fromApiPayload(data: any): TokenEnrollmentData {
    return {} as TokenEnrollmentData;
  }

  fromTokenDetailsToEnrollmentData(details: TokenDetails): TokenEnrollmentData {
    return {
      type: details.tokentype,
      description: details.description,
      containerSerial: details.container_serial,
      validityPeriodStart: details.info?.validity_period_start ?? undefined,
      validityPeriodEnd: details.info?.validity_period_end ?? undefined,
      user: details.username ?? undefined,
      realm: Array.isArray(details.realms) && details.realms.length > 0 ? details.realms[0] : undefined,
      pin: details.info?.pin ?? undefined,
      serial: details.serial ?? undefined,
      rollover: details.info?.rollover ?? undefined
    };
  }
}