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
import { TokenDetails } from "@services/token/token.service";
import {
  BaseApiPayloadMapper,
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "./_token-api-payload.mapper";

/**
 * The three ways a certificate token can be enrolled. It decides which parameters the
 * API call carries, so it has to travel with the enrollment data.
 */
export type CertificateIntention = "generate" | "uploadRequest" | "uploadCert";

// Interface for Certificate Token-specific enrollment data
export interface CertificateEnrollmentData extends TokenEnrollmentData {
  type: "certificate";
  caConnector?: string;
  certTemplate?: string;
  intention?: CertificateIntention;
  pem?: string;
}

export interface CertificateEnrollmentPayload extends TokenEnrollmentPayload {
  // genkey is inherited from TokenEnrollmentPayload and is only sent for "generate".
  ca?: string;
  template?: string;
  request?: string;
  certificate?: string;
}

@Injectable({ providedIn: "root" })
export class CertificateApiPayloadMapper
  extends BaseApiPayloadMapper
  implements TokenApiPayloadMapper<CertificateEnrollmentData>
{
  override toApiPayload(data: CertificateEnrollmentData): CertificateEnrollmentPayload {
    const intention: CertificateIntention = data.intention ?? "generate";
    const payload: CertificateEnrollmentPayload = { ...super.toApiPayload(data) };

    if (intention === "uploadCert") {
      if (data.pem != null) {
        payload.certificate = data.pem;
      }
    } else {
      if (data.caConnector != null) {
        payload.ca = data.caConnector;
      }
      if (data.certTemplate) {
        payload.template = data.certTemplate;
      }
      if (intention === "uploadRequest") {
        payload.request = data.pem ?? "";
      } else {
        payload.genkey = 1;
      }
    }

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      delete payload.user;
    }

    return payload;
  }

  override fromApiPayload(payload: CertificateEnrollmentPayload): CertificateEnrollmentData {
    const data: CertificateEnrollmentData = {
      ...super.fromApiPayload(payload),
      type: "certificate",
      ...(payload.ca != null && { caConnector: payload.ca }),
      ...(payload.template != null && { certTemplate: payload.template })
    };
    if (payload.certificate != null) {
      data.intention = "uploadCert";
      data.pem = payload.certificate;
    } else if (payload.request != null) {
      data.intention = "uploadRequest";
      data.pem = payload.request;
    } else {
      data.intention = "generate";
    }
    return data;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): CertificateEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "certificate",
      intention: "generate",
      ...(details.info?.CA != null && { caConnector: details.info?.CA })
    };
  }
}
