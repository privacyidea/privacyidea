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
import { inject, Injectable, LOCALE_ID } from "@angular/core";
import {
  clearLocaleAttempt,
  isKnownLocale,
  localeAttempted,
  localeFromPath,
  localeTargetUrl,
  markLocaleAttempt,
  normalizeLocale,
  rememberLocale
} from "@core/locale";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ThemeService } from "@services/theme/theme.service";
import { UserSettingsService, UserSettingsServiceInterface } from "@services/user-settings/user-settings.service";

export interface UiPreferencesServiceInterface {
  sync(): void;
}

/**
 * Applies the stored UI preferences of the logged-in principal: the theme is
 * applied in place, a differing language means loading another locale bundle.
 * Called once the app knows who is logged in (bootstrap with a restored session
 * and after an interactive login).
 */
@Injectable({
  providedIn: "root"
})
export class UiPreferencesService implements UiPreferencesServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly userSettingsService: UserSettingsServiceInterface = inject(UserSettingsService);
  private readonly themeService = inject(ThemeService);
  private readonly localeId = inject(LOCALE_ID);

  public sync(): void {
    if (!this.authService.isAuthenticated()) {
      return;
    }
    this.userSettingsService.getSettings().subscribe({
      next: (settings) => {
        if (settings.theme !== undefined) {
          this.themeService.applyStoredTheme(settings.theme);
        }
        this.applyLocale(settings.locale);
      },
      error: () => undefined
    });
  }

  private applyLocale(stored: unknown): void {
    if (typeof stored !== "string") {
      return;
    }
    const locale = normalizeLocale(stored);
    if (!isKnownLocale(locale)) {
      return;
    }
    if (locale === normalizeLocale(this.localeId)) {
      clearLocaleAttempt();
      return;
    }
    // The URL already asking for that locale while LOCALE_ID says otherwise means the
    // bundle is missing and the server served a fallback -- navigating again would loop.
    if (locale === localeFromPath()) {
      return;
    }
    // Same fallback, but after the router has rewritten the URL: without this the
    // preference would send every page load through a pointless extra round trip.
    if (localeAttempted(locale)) {
      return;
    }
    rememberLocale(locale);
    markLocaleAttempt(locale);
    this.navigate(localeTargetUrl(locale));
  }

  protected navigate(url: string): void {
    window.location.assign(url);
  }
}
