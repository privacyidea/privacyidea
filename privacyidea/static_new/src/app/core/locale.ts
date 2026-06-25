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
