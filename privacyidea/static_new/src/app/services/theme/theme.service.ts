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
// @services/theme/theme.service.ts

import { DOCUMENT, inject, Injectable, Renderer2, RendererFactory2, Signal, signal } from "@angular/core";
import { APP_THEME_COOKIE_NAME } from "@core/constants";
import { readCookie, writeCookie } from "@core/cookie";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { UserSettingsService, UserSettingsServiceInterface } from "@services/user-settings/user-settings.service";

export type ThemeMode = "light" | "dark" | "system";

const THEME_MODES: ThemeMode[] = ["light", "dark", "system"];

@Injectable({
  providedIn: "root"
})
export class ThemeService {
  public readonly currentTheme = signal<ThemeMode>("system");
  private readonly _visualTheme = signal<"light" | "dark">("light");
  public readonly visualTheme: Signal<"light" | "dark"> = this._visualTheme.asReadonly();
  private readonly rendererFactory = inject(RendererFactory2);
  private readonly htmlElement: HTMLHtmlElement = inject(DOCUMENT).documentElement as HTMLHtmlElement;
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly userSettingsService: UserSettingsServiceInterface = inject(UserSettingsService);
  private renderer: Renderer2 = this.rendererFactory.createRenderer(null, null);
  private mediaQueryListener?: (event: MediaQueryListEvent) => void;

  /**
   * Applies the theme cached in the browser. For an administrator the stored user
   * setting is the authoritative source, but it is only available after login -- the
   * cache keeps the login screen and the first paint from flashing the wrong theme.
   * For a principal of role "user" the cookie is the only place the theme lives.
   */
  public initializeTheme(): void {
    this.applyStoredTheme(readCookie(APP_THEME_COOKIE_NAME));
  }

  /**
   * Sets the theme, updates the cookie, and applies the corresponding classes to
   * the HTML element. For an administrator the choice is additionally stored as the
   * ``theme`` user setting, so it follows them to their other devices.
   * @param themeMode The themeMode to set ('light', 'dark', or 'system').
   */
  public setTheme(themeMode: ThemeMode): void {
    this.applyStoredTheme(themeMode);
    if (this.authService.isAuthenticated()) {
      this.userSettingsService.setSetting("theme", themeMode).subscribe({ error: () => undefined });
    }
  }

  /**
   * Applies a theme that is already stored (user setting or cookie) without writing
   * it back to the backend. Unknown values fall back to "system".
   */
  public applyStoredTheme(themeMode: unknown): void {
    const mode = THEME_MODES.includes(themeMode as ThemeMode) ? (themeMode as ThemeMode) : "system";
    THEME_MODES.forEach((t) => this.renderer.removeClass(this.htmlElement, t));

    this.currentTheme.set(mode);
    writeCookie(APP_THEME_COOKIE_NAME, mode);

    this.removeSystemThemeListener();
    this.applyTheme(mode);
  }

  private applyTheme(theme: ThemeMode): void {
    if (theme === "system") {
      this.renderer.removeClass(this.htmlElement, "light");
      this.renderer.removeClass(this.htmlElement, "dark");
      this.renderer.addClass(this.htmlElement, "system");

      this.syncWithSystemTheme();
      this.addSystemThemeListener();
    } else {
      this.renderer.removeClass(this.htmlElement, "light");
      this.renderer.removeClass(this.htmlElement, "dark");
      this.renderer.addClass(this.htmlElement, theme);

      this._visualTheme.set(theme);
    }
  }

  private syncWithSystemTheme(): void {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
    const newVisualTheme = prefersDark.matches ? "dark" : "light";
    this.renderer.addClass(this.htmlElement, newVisualTheme);
    this._visualTheme.set(newVisualTheme);
  }

  private addSystemThemeListener(): void {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
    this.mediaQueryListener = (event: MediaQueryListEvent) => {
      const newVisualTheme = event.matches ? "dark" : "light";
      this.renderer.removeClass(this.htmlElement, newVisualTheme === "light" ? "dark" : "light");
      this.renderer.addClass(this.htmlElement, newVisualTheme);
      this._visualTheme.set(newVisualTheme);
    };
    prefersDark.addEventListener("change", this.mediaQueryListener);
  }

  private removeSystemThemeListener(): void {
    if (this.mediaQueryListener) {
      window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", this.mediaQueryListener);
      this.mediaQueryListener = undefined;
    }
  }
}
