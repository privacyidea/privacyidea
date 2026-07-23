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

/** Mount point of the new WebUI; locale bundles live at APP_PREFIX or APP_PREFIX + "<locale>/". */
export const APP_PREFIX = "/app/v2/";

/**
 * Base href for a compiled locale bundle. The source locale (English) is served at the app
 * root without a locale subpath; every other locale lives under /app/v2/<locale>/.
 */
export function localeBaseHref(locale: string): string {
  return locale === "en" || locale.toLowerCase().startsWith("en-") ? APP_PREFIX : `${APP_PREFIX}${locale}/`;
}

/** Name of the cookie that records the explicit language choice. Read by the backend
 *  before the Accept-Language header when resolving which locale bundle to serve. */
export const LOCALE_COOKIE_NAME = "pi_ui_locale";

export interface UiLocale {
  /** Canonical locale code; matches the built bundle folder and the /app/v2/<code>/ path. */
  code: string;
  /** Endonym (the language's own name); intentionally not translated. */
  label: string;
}

/** Available UI languages. Order and codes mirror the backend DEFAULT_LANGUAGE_LIST. */
export const UI_LOCALES: UiLocale[] = [
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

export function normalizeLocale(code: string): string {
  return code === "en" || code.toLowerCase().startsWith("en-") ? "en" : code;
}

export function isKnownLocale(code: string): boolean {
  return LOCALE_CODES.has(code);
}

/**
 * The locale the current URL asks for: the leading path segment, or "en" for the
 * source-locale bundle served without one. This is the *requested* locale, which
 * differs from LOCALE_ID when the server falls back to another bundle.
 */
export function localeFromPath(): string {
  const path = window.location.pathname;
  if (!path.startsWith(APP_PREFIX)) {
    return "en";
  }
  const firstSegment = path.slice(APP_PREFIX.length).split("/", 1)[0];
  return isKnownLocale(firstSegment) ? firstSegment : "en";
}

/** The in-app route after the /app/v2/ prefix and any leading locale segment. */
export function currentSubPath(): string {
  const path = window.location.pathname;
  if (!path.startsWith(APP_PREFIX)) {
    return "";
  }
  const rest = path.slice(APP_PREFIX.length);
  const firstSegment = rest.split("/", 1)[0];
  return isKnownLocale(firstSegment) ? rest.slice(firstSegment.length + 1) : rest;
}

/**
 * URL of the given locale's bundle keeping the current in-app route (plus query and
 * hash), so applying a language does not bounce the user through the root redirect.
 */
export function localeTargetUrl(code: string): string {
  return localeBaseHref(code) + currentSubPath() + window.location.search + window.location.hash;
}

/** Records the explicit language choice for a year, so it survives reloads and deep links. */
export function rememberLocale(code: string): void {
  document.cookie = `${LOCALE_COOKIE_NAME}=${code}; path=/; max-age=31536000; SameSite=Lax`;
}

/** Session storage key holding the locale a bundle load was last attempted for. */
const LOCALE_ATTEMPT_KEY = "pi_ui_locale_attempt";

/**
 * Records that the bundle of ``code`` is being loaded. If the app comes back up in a
 * different locale, that bundle is not available (not built, or the dev server only
 * serves one locale) and the attempt must not be repeated on every page load.
 */
export function markLocaleAttempt(code: string): void {
  sessionStorage.setItem(LOCALE_ATTEMPT_KEY, code);
}

export function localeAttempted(code: string): boolean {
  return sessionStorage.getItem(LOCALE_ATTEMPT_KEY) === code;
}

export function clearLocaleAttempt(): void {
  sessionStorage.removeItem(LOCALE_ATTEMPT_KEY);
}
