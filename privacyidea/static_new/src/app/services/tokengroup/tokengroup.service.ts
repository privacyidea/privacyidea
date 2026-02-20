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
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { lastValueFrom } from "rxjs";

type Tokengroups = {
  [key: string]: _Tokengroup;
};

interface _Tokengroup {
  description: string;
  id: number;
}

export interface Tokengroup {
  groupname: string;
  description: string;
  id?: number;
}

export interface TokengroupServiceInterface {
  tokengroupResource: HttpResourceRef<PiResponse<Tokengroups> | undefined>;
  tokengroups: WritableSignal<Tokengroup[]>;
  postTokengroup(tokengroup: Tokengroup): Promise<void>;
  deleteTokengroup(groupname: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class TokengroupService implements TokengroupServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  private readonly tokengroupBaseUrl = environment.proxyUrl + "/tokengroup/";

  tokengroupResource = httpResource<PiResponse<Tokengroups>>(() => ({
    url: this.tokengroupBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  tokengroups: WritableSignal<Tokengroup[]> = linkedSignal({
    source: this.tokengroupResource.value,
    computation: (source, previous) => {
      const value = source?.result?.value;
      if (!value) {
        return previous?.value ?? [];
      }
      return Object.entries(value).map(([groupname, { description, id }]) => ({
        groupname,
        description,
        id
      }));
    }
  });

  async postTokengroup(tokengroup: Tokengroup): Promise<void> {
    const url = `${this.tokengroupBaseUrl}${tokengroup.groupname}`;
    const request = this.http.post<PiResponse<any>>(url, tokengroup, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved tokengroup.`);
        this.tokengroupResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save tokengroup. ` + message);
        throw new Error("post-failed");
      });
  }

  async deleteTokengroup(groupname: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.tokengroupBaseUrl}${groupname}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted tokengroup: ${groupname}.`);
        this.tokengroupResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete tokengroup. ` + message);
        throw new Error("delete-failed");
      });
  }
}
