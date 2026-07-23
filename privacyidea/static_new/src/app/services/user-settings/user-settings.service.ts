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
import { inject, Injectable, Signal, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { catchError, map, Observable, of, shareReplay, tap, throwError } from "rxjs";

/**
 * The top-level setting keys the backend accepts. Mirrors KNOWN_SETTING_KEYS in
 * privacyidea/lib/usersetting.py; a key that is not listed there is rejected.
 */
export type UserSettingKey = "theme" | "locale" | "starting_page" | "token_columns" | "dashboard" | "pinned_items";

export type UserSettings = Partial<Record<UserSettingKey, unknown>>;

export interface UserSettingsServiceInterface {
  readonly settings: Signal<UserSettings | null>;

  getSettings(): Observable<UserSettings>;

  getSetting<T>(key: UserSettingKey): Observable<T | null>;

  setSetting<T>(key: UserSettingKey, value: T): Observable<UserSettings>;

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

  public readonly settings: Signal<UserSettings | null> = this.cache.asReadonly();

  public getSettings(): Observable<UserSettings> {
    const cached = this.cache();
    if (cached) {
      return of(cached);
    }
    if (!this.request) {
      this.request = this.http
        .get<PiResponse<UserSettings>>(this.baseUrl, { headers: this.authService.getHeaders() })
        .pipe(
          map((response) => response.result?.value ?? {}),
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
    return this.http
      .post<PiResponse<UserSettings>>(
        this.baseUrl,
        { settings: { [key]: value } },
        { headers: this.authService.getHeaders() }
      )
      .pipe(
        map((response) => response.result?.value ?? {}),
        tap((settings) => this.store(settings)),
        catchError((error) => this.fail(error, "Failed to save the user settings."))
      );
  }

  public deleteSetting(key: UserSettingKey): Observable<UserSettings> {
    return this.http
      .delete<PiResponse<UserSettings>>(`${this.baseUrl}/${encodeURIComponent(key)}`, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? {}),
        tap((settings) => this.store(settings)),
        catchError((error) => this.fail(error, "Failed to reset the user settings."))
      );
  }

  public clearCache(): void {
    this.cache.set(null);
    this.request = null;
  }

  private store(settings: UserSettings): void {
    this.cache.set(settings);
    this.request = null;
  }

  private fail(error: unknown, message: string): Observable<never> {
    this.request = null;
    console.error(message, error);
    this.notificationService.error(message);
    return throwError(() => error);
  }
}
