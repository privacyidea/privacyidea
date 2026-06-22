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
import { Component, inject, LOCALE_ID } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";
import { APP_PREFIX, localeBaseHref } from "@core/locale";

interface UiLocale {
  /** Canonical locale code; matches the built bundle folder and the /app/v2/<code>/ path. */
  code: string;
  /** Endonym (the language's own name); intentionally not translated. */
  label: string;
}

/** Name of the cookie that records the explicit language choice. Read by the backend
 *  before the Accept-Language header when resolving which locale bundle to serve. */
export const LOCALE_COOKIE_NAME = "pi_ui_locale";

/** Available UI languages. Order and codes mirror the backend DEFAULT_LANGUAGE_LIST. */
const UI_LOCALES: UiLocale[] = [
  { code: "en", label: "English" },
  { code: "de", label: "Deutsch" },
  { code: "nl", label: "Nederlands" },
  { code: "zh-Hant", label: "繁體中文" },
  { code: "fr", label: "Français" },
  { code: "es", label: "Español" },
  { code: "tr", label: "Türkçe" },
  { code: "cs", label: "Čeština" },
  { code: "it", label: "Italiano" },
  { code: "ta", label: "தமிழ்" },
  { code: "pt", label: "Português" },
  { code: "ru", label: "Русский" },
  { code: "uk", label: "Українська" }
];

/** Locale codes that may appear as the first path segment of an /app/v2/ URL. */
const LOCALE_CODES = new Set(UI_LOCALES.map((locale) => locale.code));

@Component({
  selector: "app-language-switcher",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  templateUrl: "./language-switcher.component.html"
})
export class LanguageSwitcherComponent {
  private readonly localeId = inject(LOCALE_ID);
  protected readonly locales = UI_LOCALES;
  protected readonly currentLocale = this.normalize(this.localeId);

  private normalize(code: string): string {
    return code === "en" || code.toLowerCase().startsWith("en-") ? "en" : code;
  }

  protected switchTo(code: string): void {
    if (code === this.currentLocale) {
      return;
    }
    // Persist the explicit choice for a year. The backend reads this before the
    // Accept-Language header, so the preference survives reloads and deep links.
    document.cookie = `${LOCALE_COOKIE_NAME}=${code}; path=/; max-age=31536000; SameSite=Lax`;
    // later: when authenticated, also persist this to /user/settings as the user's
    // language preference and reconcile the cookie from it on login.
    // Each locale is a separately compiled bundle, so applying a language is a full-page
    // navigation. Preserve the current in-app route (plus query/hash) so the user stays on
    // the same page instead of bouncing through the root -> login redirect after the reload.
    this.navigate(localeBaseHref(code) + this.currentSubPath() + window.location.search + window.location.hash);
  }

  /** The in-app route after the /app/v2/ prefix and any leading locale segment. */
  private currentSubPath(): string {
    const path = window.location.pathname;
    if (!path.startsWith(APP_PREFIX)) {
      return "";
    }
    const rest = path.slice(APP_PREFIX.length);
    const firstSegment = rest.split("/", 1)[0];
    return LOCALE_CODES.has(firstSegment) ? rest.slice(firstSegment.length + 1) : rest;
  }

  protected navigate(url: string): void {
    window.location.assign(url);
  }
}
