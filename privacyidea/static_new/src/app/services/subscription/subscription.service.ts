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
import { HttpClient, httpResource } from "@angular/common/http";
import { effect, inject, Injectable, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { catchError, Observable, throwError } from "rxjs";

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

/** State of the subscription record itself, independent of whether the client is used. */
export type SubscriptionState = "none" | "valid" | "expiring" | "exceeded" | "expired";

/**
 * One row of the dashboard subscription overview, as returned by GET /subscriptions/status.
 * The server itself is reported as an entry with is_server set.
 */
export interface SubscriptionStatus {
  application: string;
  is_server?: boolean;
  /** Whether the component is actively used: it has a subscription or was seen recently. */
  in_use: boolean;
  subscription: SubscriptionState;
  /** Last time a client of this component was seen, null if never. */
  last_seen: string | null;
  date_till: string | null;
  /** Days until date_till; negative once it has passed. */
  days_left: number | null;
  /** Versions seen in the clients' user agents, newest first. */
  versions: string[];
  /** Latest released version of this component, null if it could not be determined. */
  current_version: string | null;
  current_version_date: string | null;
  current_version_url: string | null;
}

@Injectable()
export class SubscriptionService {
  private readonly authService = inject(AuthService);
  private readonly contentService = inject(ContentService);
  private readonly notificationService = inject(NotificationService);
  private readonly http = inject(HttpClient);

  private baseUrl = environment.proxyUrl + "/subscriptions";
  private reloadTrigger = signal(0);
  subscriptionsResource = httpResource<PiResponse<Record<string, Subscription>>>(() => {
    this.reloadTrigger();
    if (!this.contentService.onSubscription()) {
      return undefined;
    }
    return {
      url: `${this.baseUrl}/`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.subscriptionsResource.error(), "subscriptions");
    });
  }

  reload(): void {
    this.reloadTrigger.update((v) => v + 1);
  }

  getSubscriptions(): Observable<PiResponse<Record<string, Subscription>>> {
    return this.http.get<PiResponse<Record<string, Subscription>>>(`${this.baseUrl}/`, {
      headers: this.authService.getHeaders()
    });
  }

  getSubscriptionStatus(): Observable<PiResponse<SubscriptionStatus[]>> {
    return this.http.get<PiResponse<SubscriptionStatus[]>>(`${this.baseUrl}/status`, {
      headers: this.authService.getHeaders()
    });
  }

  deleteSubscription(application: string): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete<PiResponse<boolean>>(`${this.baseUrl}/${encodeURIComponent(application)}`, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to delete subscription.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error(
            $localize`:@@subscription.failedToDeleteSubscription:Failed to delete subscription. ${message}:MESSAGE:`
          );
          return throwError(() => error);
        })
      );
  }

  uploadSubscriptionFile(file: File): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    const formData = new FormData();
    formData.append("file", file);

    return this.http.post<PiResponse<boolean>>(`${this.baseUrl}/`, formData, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to upload subscription file.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error(
          $localize`:@@subscription.failedToUploadSubscriptionFile:Failed to upload subscription file. ${message}:MESSAGE:`
        );
        return throwError(() => error);
      })
    );
  }
}
