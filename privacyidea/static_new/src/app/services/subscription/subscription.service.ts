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
import { inject, Injectable, signal } from "@angular/core";
import { HttpClient, httpResource } from "@angular/common/http";
import { AuthService } from "../auth/auth.service";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { catchError, Observable, throwError } from "rxjs";
import { NotificationService } from "../notification/notification.service";

export interface Subscription {
  application: string;
  timedelta: number;
  level: string;
  num_users: number;
  active_users: number;
  num_tokens: number;
  active_tokens: number;
  num_clients: number;
  date_from: string;
  date_till: string;
  for_name: string;
  for_email: string;
  for_address: string;
  for_phone: string;
  for_url: string;
  for_comment: string;
  by_name: string;
  by_url: string;
  by_address: string;
  by_email: string;
  by_phone: string;
}

@Injectable({
  providedIn: "root"
})
export class SubscriptionService {
  private http = inject(HttpClient);
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);

  private baseUrl = environment.proxyUrl + "/subscriptions";
  
  private reloadTrigger = signal(0);

  subscriptionsResource = httpResource<PiResponse<Record<string, Subscription>>>(() => {
    this.reloadTrigger();
    return {
      url: `${this.baseUrl}/`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  reload(): void {
    this.reloadTrigger.update(v => v + 1);
  }

  deleteSubscription(application: string): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http.delete<PiResponse<boolean>>(`${this.baseUrl}/${application}`, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to delete subscription.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete subscription. " + message);
        return throwError(() => error);
      })
    );
  }

  uploadSubscriptionFile(file: File): Observable<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    const formData = new FormData();
    formData.append("file", file);

    return this.http.post<PiResponse<any>>(`${this.baseUrl}/`, formData, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to upload subscription file.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to upload subscription file. " + message);
        return throwError(() => error);
      })
    );
  }
}
