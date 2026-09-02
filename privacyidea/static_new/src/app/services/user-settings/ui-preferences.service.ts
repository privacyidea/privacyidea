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
import { computed, inject, Injectable, LOCALE_ID, Signal, signal } from "@angular/core";
import { Observable, catchError, map, of, shareReplay } from "rxjs";
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
import { DEFAULT_LANDING_PAGE, isLandingPage, LANDING_PAGES, LandingPage } from "@core/landing-page";
import { AppearanceService } from "@services/appearance/appearance.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ThemeService } from "@services/theme/theme.service";
import { UserSettingsService, UserSettingsServiceInterface } from "@services/user-settings/user-settings.service";

export interface UiPreferencesServiceInterface {
  readonly preferredLocale: Signal<string>;

  readonly showLoadingUrls: Signal<boolean>;

  readonly landingPage: Signal<LandingPage>;

  readonly availableLandingPages: Signal<LandingPage[]>;

  landingPage$(): Observable<LandingPage>;

  setShowLoadingUrls(show: boolean): Observable<unknown>;

  setLandingPage(page: LandingPage): void;

  resetLandingPage(): Observable<unknown>;

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
  private readonly appearanceService = inject(AppearanceService);
  private readonly localeId = inject(LOCALE_ID);
  private readonly _showLoadingUrls = signal(false);

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

  /** Whether the endpoints in flight are listed on screen while the loading bar shows. */
  public readonly showLoadingUrls: Signal<boolean> = this._showLoadingUrls.asReadonly();

  /**
   * The page the principal is sent to right after login. Falls back to the
   * dashboard when the ADMIN_DASHBOARD policy allows it, otherwise the token
   * list -- a stored choice that is no longer available (policy withdrawn,
   * right revoked) falls back the same way rather than routing to a page the
   * principal cannot see.
   */
  public readonly landingPage: Signal<LandingPage> = computed(() => {
    const stored = this.userSettingsService.settings()?.starting_page;
    if (isLandingPage(stored) && this.isLandingPageAvailable(stored)) {
      return stored;
    }
    return this.authService.adminDashboard() ? "dashboard" : DEFAULT_LANDING_PAGE;
  });

  /** The landing pages the principal currently has the rights to see, in display order. */
  public readonly availableLandingPages: Signal<LandingPage[]> = computed(() =>
    LANDING_PAGES.filter((page) => this.isLandingPageAvailable(page))
  );

  /**
   * Reports once the write has settled, so a caller that also navigates away -- switching
   * locale is a full-page load, which would abort a write mid-flight -- can wait for it first.
   */
  public setShowLoadingUrls(show: boolean): Observable<unknown> {
    this._showLoadingUrls.set(show);
    const write$ = this.userSettingsService.setSetting("show_loading_urls", show).pipe(
      catchError(() => of(null)),
      shareReplay(1)
    );
    write$.subscribe();
    return write$;
  }

  /**
   * Like `landingPage`, but waits for the stored settings to have loaded (or failed) first.
   * `landingPage` reads a signal that starts out `null` until the `/user/settings` GET
   * resolves -- evaluated synchronously right after login, before that request has had a
   * chance to complete, it would always fall through to the policy-driven default. Routing
   * decisions taken at that moment (the post-login redirect, the login guard) need this
   * variant instead so a stored choice is honored on the very first navigation.
   */
  public landingPage$(): Observable<LandingPage> {
    return this.userSettingsService.getSettings().pipe(
      map(() => this.landingPage()),
      catchError(() => of(this.landingPage()))
    );
  }

  /** Persists the picked landing page. */
  public setLandingPage(page: LandingPage): void {
    this.userSettingsService.setSetting("starting_page", page).subscribe({ error: () => undefined });
  }

  /** Reverts to the policy-driven default (dashboard, or the token list). */
  public resetLandingPage(): Observable<unknown> {
    return this.userSettingsService.deleteSetting("starting_page");
  }

  private isLandingPageAvailable(page: LandingPage): boolean {
    switch (page) {
      case "dashboard":
        return this.authService.adminDashboard();
      case "users":
        return this.authService.actionAllowed("userlist");
      case "audit":
        return this.authService.actionAllowed("auditlog");
      case "tokens":
        return true;
    }
  }

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
        this._showLoadingUrls.set(settings.show_loading_urls === true);
        // An absent key leaves the cookie-cached appearance in place.
        if (settings.depth !== undefined) {
          this.appearanceService.applyStoredDepth(settings.depth);
        }
        if (settings.light_source !== undefined) {
          this.appearanceService.applyStoredLightSource(settings.light_source);
        }
        if (settings.corner_radius !== undefined) {
          this.appearanceService.applyStoredCorners(settings.corner_radius);
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
