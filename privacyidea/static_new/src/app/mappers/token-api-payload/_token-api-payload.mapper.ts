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
import { TokenDetails, TokenTypeKey } from "../../services/token/token.service";

export interface EnrollmentResponse<D extends EnrollmentResponseDetail = EnrollmentResponseDetail> {
  type: string;
  detail: D;
  result: { status: boolean };

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
  verify?: { message: string };

  [key: string]: any;
}

export interface EnrollmentUrl {
  description: string;
  img: string;
  value: string;
  value_b32?: string;
}

export type TokenEnrollmentData = {
  type: TokenTypeKey;
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
  verify?: string;
  [key: string]: any; // TODO: remove this when all types are defined
};

export interface TokenEnrollmentPayload {
  type: TokenTypeKey;
  description?: string;
  container_serial?: string;
  validity_period_start?: string;
  validity_period_end?: string;
  user?: string | boolean;
  realm?: string;
  pin?: string;
  rollover?: boolean;
  serial?: string;
  hashlib?: string;
  otplen?: number;
  timeStep?: string | number;
  genkey?: boolean | number;
  [key: string]: any; // TODO: remove this when all types are defined
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
      ...(data.description && { description: data.description }),
      ...(data.containerSerial && { container_serial: data.containerSerial }),
      ...(data.validityPeriodStart && { validity_period_start: data.validityPeriodStart }),
      ...(data.validityPeriodEnd && { validity_period_end: data.validityPeriodEnd }),
      ...(data.user && { user: data.user }),
      ...(data.realm && data.user && { realm: data.realm }),
      ...(data.pin && { pin: data.pin }),
      ...(data.serial && { serial: data.serial }),
      ...(data.rollover != null && { rollover: data.rollover })
    };
  }

  fromApiPayload(data: TokenEnrollmentPayload): TokenEnrollmentData {
    return {
      type: data.type,
      ...(data.description && { description: data.description }),
      ...(data.container_serial && { containerSerial: data.container_serial }),
      ...(data.validity_period_start && { validityPeriodStart: data.validity_period_start }),
      ...(data.validity_period_end && { validityPeriodEnd: data.validity_period_end }),
      ...(typeof data.user === "string" && { user: data.user }),
      ...(data.realm && { realm: data.realm }),
      ...(data.pin && { pin: data.pin }),
      ...(data.serial && { serial: data.serial }),
      ...(data.rollover != null && { rollover: data.rollover })
    };
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
