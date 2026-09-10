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

/**
 * Where the WebUI keeps the session of the logged-in user. The server decides through the
 * `session_persistence` WebUI policy, so the browser only ever follows: "tab" keeps the session
 * in the tab it was opened in and ends it when that tab closes, "browser" shares the session with
 * every tab of the browser and leaves it on disk until the JWT expires.
 */
export type SessionPersistence = "tab" | "browser";

export const SESSION_PERSISTENCE_VALUES: SessionPersistence[] = ["tab", "browser"];

export const DEFAULT_SESSION_PERSISTENCE: SessionPersistence = "tab";

export function isSessionPersistence(value: unknown): value is SessionPersistence {
  return typeof value === "string" && (SESSION_PERSISTENCE_VALUES as string[]).includes(value);
}
