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

// Interface for Registration Token-specific enrollment data
export interface RegistrationEnrollmentData extends TokenEnrollmentData {
  type: "registration";
}

export interface RegistrationEnrollmentPayload extends TokenEnrollmentPayload {
  serial?: string | null;
}

@Injectable({ providedIn: "root" })
export class RegistrationApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<RegistrationEnrollmentData> {

  override toApiPayload(data: RegistrationEnrollmentData): RegistrationEnrollmentPayload {
    // No type-specific fields in switch statement for 'registration'
    const payload: RegistrationEnrollmentPayload = super.toApiPayload(data);

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    return payload;
  }

  override fromApiPayload(payload: any): RegistrationEnrollmentData {
    // Placeholder: Implement transformation from API payload.
    return payload as RegistrationEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): RegistrationEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "registration"
    };
  }
}
