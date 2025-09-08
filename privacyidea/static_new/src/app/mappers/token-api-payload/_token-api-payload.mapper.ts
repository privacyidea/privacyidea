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
  detail: D;

  [key: string]: any;
}

export interface EnrollmentResponseDetail {
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
  description: string;
  containerSerial: string;
  validityPeriodStart: string;
  validityPeriodEnd: string;
  user: string;
  realm: string;
  onlyAddToRealm?: boolean;
  pin: string;
  serial: string | null;
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
}

export interface TokenApiPayloadMapper<T> {
  toApiPayload(data: T): any;

  fromApiPayload(data: any): T;
}
