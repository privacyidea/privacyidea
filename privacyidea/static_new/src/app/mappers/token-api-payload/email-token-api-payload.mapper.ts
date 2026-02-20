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
import { parseBooleanValue } from "../../utils/parse-boolean-value";

export interface EmailEnrollmentData extends TokenEnrollmentData {
  type: "email";
  emailAddress?: string;
  readEmailDynamically?: boolean;
}

export interface EmailEnrollmentPayload extends TokenEnrollmentPayload {
  email?: string;
  dynamic_email: boolean;
}

@Injectable({ providedIn: "root" })
export class EmailApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<EmailEnrollmentData> {

  override toApiPayload(data: EmailEnrollmentData): EmailEnrollmentPayload {
    const basePayload = super.toApiPayload(data);
    const payload: EmailEnrollmentPayload = {
      ...basePayload,
      ...(data.emailAddress !== undefined && { email: data.emailAddress }),
      dynamic_email: !!data.readEmailDynamically
    };
    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.email === undefined) {
      delete payload.email;
    }
    return payload;
  }

  override fromApiPayload(payload: any): EmailEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as EmailEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): EmailEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "email",
      emailAddress: details.info?.email ?? undefined,
      readEmailDynamically: parseBooleanValue(details.info?.dynamic_email ?? false)
    };
  }
}
