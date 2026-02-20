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

// Interface for Certificate Token-specific enrollment data
export interface CertificateEnrollmentData extends TokenEnrollmentData {
  type: "certificate";
  caConnector?: string;
  certTemplate?: string;
  pem?: string;
  // genkey=1 is hardcoded in TokenService
}

export interface CertificateEnrollmentPayload extends TokenEnrollmentPayload {
  genkey: 1;
  ca?: string;
  template?: string;
  pem?: string;
}

@Injectable({ providedIn: "root" })
export class CertificateApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<CertificateEnrollmentData> {

  override toApiPayload(data: CertificateEnrollmentData): CertificateEnrollmentPayload {
    const payload: CertificateEnrollmentPayload = {
      ...super.toApiPayload(data),
      genkey: 1, // As per switch statement
      ...(data.caConnector != null && { ca: data.caConnector }),
      ...(data.certTemplate != null && { template: data.certTemplate }),
      ...(data.pem != null && { pem: data.pem })
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }

    return payload;
  }

  override fromApiPayload(payload: any): CertificateEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as CertificateEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): CertificateEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "certificate",
      ...(details.info?.CA != null && { caConnector: details.info?.CA })
    };
  }
}
