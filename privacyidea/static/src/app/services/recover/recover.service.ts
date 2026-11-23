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
import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { Observable } from "rxjs";

export interface RecoverRequestParams {
  user: string;
  realm?: string;
  email: string;
}

export interface RecoverResetParams {
  user: string;
  realm?: string;
  recoverycode: string;
  password: string;
}

export interface RecoverServiceInterface {
  requestRecoveryCode(params: RecoverRequestParams): Observable<PiResponse<boolean>>;

  resetPassword(params: RecoverResetParams): Observable<PiResponse<boolean>>;
}

/**
 * The anonymous endpoints of the password recovery: the first one emails a recovery code to the user,
 * the second one consumes it and sets the new password.
 */
@Injectable({ providedIn: "root" })
export class RecoverService implements RecoverServiceInterface {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.proxyUrl + "/recover";

  requestRecoveryCode(params: RecoverRequestParams): Observable<PiResponse<boolean>> {
    return this.http.post<PiResponse<boolean>>(this.baseUrl, params);
  }

  resetPassword(params: RecoverResetParams): Observable<PiResponse<boolean>> {
    return this.http.post<PiResponse<boolean>>(`${this.baseUrl}/reset`, params);
  }
}
