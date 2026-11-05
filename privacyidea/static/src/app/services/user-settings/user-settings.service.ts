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
import { HttpClient, HttpErrorResponse } from "@angular/common/http";
import { computed, inject, Injectable, Signal, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { catchError, filter, map, Observable, of, shareReplay, tap, throwError } from "rxjs";

/**
 * The settings the backend accepts. It rejects any other top-level key, so a new
 * setting has to be added to KNOWN_SETTING_KEYS in privacyidea/lib/usersetting.py
 * as well.
 */
export type UserSettingKey =
  | "theme"
  | "locale"
  | "show_loading_urls"
  | "depth"
  | "light_source"
  | "corner_radius"
  | "status_colors"
  | "dashboard"
  | "starting_page";

export type UserSettings = Partial<Record<UserSettingKey, unknown>>;

export interface UserSettingsServiceInterface {
  readonly settings: Signal<UserSettings | null>;

  readonly available: Signal<boolean>;

  getSettings(): Observable<UserSettings>;

  getSetting<T>(key: UserSettingKey): Observable<T | null>;

  setSetting<T>(key: UserSettingKey, value: T): Observable<UserSettings>;

  setSettings(values: Partial<Record<UserSettingKey, unknown>>): Observable<UserSettings>;

  deleteSetting(key: UserSettingKey): Observable<UserSettings>;

  clearCache(): void;
}

@Injectable({
  providedIn: "root"
})
export class UserSettingsService implements UserSettingsServiceInterface {
  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  private readonly baseUrl = environment.proxyUrl + "/user/settings";
  private readonly cache = signal<UserSettings | null>(null);
  private request: Observable<UserSettings> | null = null;
  // Counts the calls of clearCache(), so an answer to a request sent before one can be told apart.
  private epoch = 0;

  public readonly settings: Signal<UserSettings | null> = this.cache.asReadonly();

  /**
   * Stored settings exist for administrators only. A principal of role "user" keeps
   * theme and language in the browser (cookie and local storage), so no request is
   * sent for them and every read answers with an empty document.
   */
  public readonly available: Signal<boolean> = computed(
    () => this.authService.isAuthenticated() && this.authService.role() !== "user"
  );

  public getSettings(): Observable<UserSettings> {
    if (!this.available()) {
      return of({});
    }
    const cached = this.cache();
    if (cached) {
      return of(cached);
    }
    if (!this.request) {
      const epoch = this.epoch;
      this.request = this.http
        .get<PiResponse<UserSettings>>(this.baseUrl, { headers: this.authService.getHeaders() })
        .pipe(
          map((response) => response.result?.value ?? {}),
          // An answer to a request from a session that has since ended is dropped before it is cached or reaches
          // a subscriber: clearCache() has moved on, and the next login must not see the ended session's settings.
          filter(() => epoch === this.epoch),
          tap((settings) => this.store(settings)),
          catchError((error) => this.fail(error, "Failed to load the user settings.")),
          shareReplay(1)
        );
    }
    return this.request;
  }

  public getSetting<T>(key: UserSettingKey): Observable<T | null> {
    return this.getSettings().pipe(map((settings) => (settings[key] as T | undefined) ?? null));
  }

  public setSetting<T>(key: UserSettingKey, value: T): Observable<UserSettings> {
    if (!this.available()) {
      return of({});
    }
    const epoch = this.epoch;
    return this.http
      .post<
        PiResponse<UserSettings>
      >(this.baseUrl, { settings: { [key]: value } }, { headers: this.authService.getHeaders() })
      .pipe(
        map((response) => response.result?.value ?? {}),
        tap((settings) => this.storeIfCurrent(settings, epoch)),
        catchError((error) => this.fail(error, "Failed to save the user settings."))
      );
  }

  /** Merges several keys in one request, so a caller setting more than one avoids one POST per key. */
  public setSettings(values: Partial<Record<UserSettingKey, unknown>>): Observable<UserSettings> {
    if (!this.available()) {
      return of({});
    }
    const epoch = this.epoch;
    return this.http
      .post<PiResponse<UserSettings>>(this.baseUrl, { settings: values }, { headers: this.authService.getHeaders() })
      .pipe(
        map((response) => response.result?.value ?? {}),
        tap((settings) => this.storeIfCurrent(settings, epoch)),
        catchError((error) => this.fail(error, "Failed to save the user settings."))
      );
  }

  public deleteSetting(key: UserSettingKey): Observable<UserSettings> {
    if (!this.available()) {
      return of({});
    }
    const epoch = this.epoch;
    return this.http
      .delete<PiResponse<UserSettings>>(`${this.baseUrl}/${encodeURIComponent(key)}`, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? {}),
        tap((settings) => this.storeIfCurrent(settings, epoch)),
        catchError((error) => this.fail(error, "Failed to reset the user settings."))
      );
  }

  public clearCache(): void {
    this.epoch++;
    this.cache.set(null);
    this.request = null;
  }

  /** The answer to a write sent before clearCache() belongs to a session that ended and is not cached. */
  private storeIfCurrent(settings: UserSettings, epoch: number): void {
    if (epoch === this.epoch) {
      this.store(settings);
    }
  }

  private store(settings: UserSettings): void {
    this.cache.set(settings);
    this.request = null;
  }

  private fail(error: unknown, message: string): Observable<never> {
    this.request = null;
    console.error(message, error);
    const detail = (error as HttpErrorResponse)?.error?.result?.error?.message || "";
    this.notificationService.error(detail ? `${message} ${detail}` : message);
    return throwError(() => error);
  }
}
