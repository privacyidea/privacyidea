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

// Interface for Question Token-specific enrollment data
export interface QuestionEnrollmentData extends TokenEnrollmentData {
  type: "question";
  answers?: Record<string, string>; // Mapped to 'questions' in payload
}

export interface QuestionEnrollmentPayload extends TokenEnrollmentPayload {
  questions?: Record<string, string>;
}

@Injectable({ providedIn: "root" })
export class QuestionApiPayloadMapper extends BaseApiPayloadMapper implements TokenApiPayloadMapper<QuestionEnrollmentData> {

  override toApiPayload(data: QuestionEnrollmentData): QuestionEnrollmentPayload {
    const payload: QuestionEnrollmentPayload = {
      ...super.toApiPayload(data),
      questions: data.answers
    };

    if (data.onlyAddToRealm) {
      payload.realm = data.realm;
      payload.user = null;
    }
    if (payload.questions === undefined) {
      delete payload.questions;
    }
    return payload;
  }

  override fromApiPayload(payload: any): QuestionEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as QuestionEnrollmentData;
  }

  override fromTokenDetailsToEnrollmentData(details: TokenDetails): QuestionEnrollmentData {
    return {
      ...super.fromTokenDetailsToEnrollmentData(details),
      type: "question"
    };
  }
}
