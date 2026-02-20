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

export interface FourEyesEnrollmentData extends TokenEnrollmentData {
  type: "4eyes";
  separator: string;
  requiredTokenOfRealms: {
    realm: string;
    tokens: number;
  }[];
}

export interface FourEyesEnrollmentPayload extends TokenEnrollmentPayload {
  separator: string;
  "4eyes": { [key: string]: { count: number; selected: boolean } };
}

@Injectable({ providedIn: "root" })
export class FourEyesApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<FourEyesEnrollmentData> {

  override toApiPayload(data: FourEyesEnrollmentData): FourEyesEnrollmentPayload {
    const basePayload = super.toApiPayload(data);
    const payload: FourEyesEnrollmentPayload = {
      ...basePayload,
      separator: data.separator,
      "4eyes": (data.requiredTokenOfRealms ?? []).reduce(
        (acc: { [key: string]: { count: number; selected: boolean } }, curr) => {
          acc[curr.realm] = { count: curr.tokens, selected: true };
          return acc;
        },
        {}
      )
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    return payload;
  }

  override fromApiPayload(payload: any): FourEyesEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as FourEyesEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): FourEyesEnrollmentData {
    let requiredTokenOfRealms: { realm: string; tokens: number }[] = [];
    const fourEyesString = details.info?.["4eyes"];
    if (typeof fourEyesString === "string" && fourEyesString.trim() !== "") {
      requiredTokenOfRealms = fourEyesString.split(",").map((entry) => {
        const [realm, tokens] = entry.split(":");
        return {
          realm: realm?.trim() ?? "",
          tokens: Number(tokens)
        };
      }).filter(item => item.realm && !isNaN(item.tokens));
    }
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "4eyes",
      separator: details.info?.separator ?? "",
      requiredTokenOfRealms
    };
  }
}
