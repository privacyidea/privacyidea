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
import { computed, inject, Injectable, LOCALE_ID, Signal } from "@angular/core";
import {
  clearLocaleAttempt,
  isKnownLocale,
  localeAttempted,
  localeFromPath,
  localeSegmentFromPath,
  localeTargetUrl,
  markLocaleAttempt,
  normalizeLocale,
  rememberLocale
} from "@core/locale";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ThemeService } from "@services/theme/theme.service";
import { UserSettingsService, UserSettingsServiceInterface } from "@services/user-settings/user-settings.service";

export interface UiPreferencesServiceInterface {
  readonly preferredLocale: Signal<string>;

  normalizeLocaleUrl(): void;

  sync(): void;

  switchLocale(code: string): void;
}

/**
 * Owns the UI preferences of the logged-in principal: applying what is stored
 * (sync) and changing the language (switchLocale). The theme is applied in
 * place, a differing language means loading another locale bundle. sync is
 * called once the app knows who is logged in (bootstrap with a restored session
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

  /** The locale of the bundle the app is currently running in. */
  public readonly currentLocale = normalizeLocale(this.localeId);

  /**
   * The language the user picked, which is not necessarily the one running: a bundle the
   * server does not provide falls back to another locale. The switchers offer this value
   * as the selected one, so a stored preference stays correctable from the UI even while
   * a different bundle is running.
   */
  public readonly preferredLocale: Signal<string> = computed(() => {
    const stored = this.userSettingsService.settings()?.locale;
    if (typeof stored === "string") {
      const locale = normalizeLocale(stored);
      if (isKnownLocale(locale)) {
        return locale;
      }
    }
    return this.currentLocale;
  });

  /**
   * Aligns the URL with the bundle that is actually running. A path asking for a locale the
   * server did not serve leaves the app on a route the router cannot resolve -- and a
   * logged-in principal then ends up on the landing page instead of the page they asked for.
   * Runs before the first navigation, so the requested page survives the correction.
   */
  public normalizeLocaleUrl(): void {
    const requested = localeSegmentFromPath();
    if (requested === null || requested === this.currentLocale) {
      return;
    }
    this.navigate(localeTargetUrl(this.currentLocale));
  }

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

  /** Applies a language the user picked: remembers the choice and loads its bundle. */
  public switchLocale(code: string): void {
    rememberLocale(code);
    if (code === this.currentLocale) {
      // The bundle is already running, so only the stored preference has to catch up --
      // no page load involved. This is the way back when a preferred bundle was missing
      // and the server served this one instead.
      clearLocaleAttempt();
      this.userSettingsService.setSetting("locale", code).subscribe({ error: () => undefined });
      return;
    }
    markLocaleAttempt(code);
    const target = localeTargetUrl(code);
    if (!this.authService.isAuthenticated()) {
      this.navigate(target);
      return;
    }
    // Each locale is a separately compiled bundle, so applying a language is a full-page
    // navigation -- which cancels in-flight requests. Store the preference first and only
    // navigate once the request settled, otherwise the setting would be lost.
    this.userSettingsService.setSetting("locale", code).subscribe({
      next: () => this.navigate(target),
      error: () => this.navigate(target)
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
    if (locale === this.currentLocale) {
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
