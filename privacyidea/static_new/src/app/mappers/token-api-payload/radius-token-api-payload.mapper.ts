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

export interface RadiusEnrollmentData extends TokenEnrollmentData {
  type: "radius";
  radiusServerConfiguration?: string;
  radiusUser?: string;
}

export interface RadiusEnrollmentPayload extends TokenEnrollmentPayload {
  "radius.identifier"?: string;
  "radius.user"?: string;
}

@Injectable({ providedIn: "root" })
export class RadiusApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<RadiusEnrollmentData> {

  override toApiPayload(data: RadiusEnrollmentData): RadiusEnrollmentPayload {
    const payload: RadiusEnrollmentPayload = {
      ...super.toApiPayload(data),
      ...(data.radiusServerConfiguration != null && { "radius.identifier": data.radiusServerConfiguration }),
      ...(data.radiusUser != null && { "radius.user": data.radiusUser })
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): RadiusEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as RadiusEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): RadiusEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "radius",
      radiusServerConfiguration: details.info?.["radius.identifier"] ?? "",
      radiusUser: details.info?.["radius.user"] ?? ""
    };
  }
}
