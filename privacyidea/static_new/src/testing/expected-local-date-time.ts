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

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Builds the string formatLocalDateTime is expected to produce for the given LOCAL date/time
 * components, without going through Intl.DateTimeFormat itself — so tests using this stay
 * independent of formatLocalDateTime's own implementation and of the machine's timezone.
 */
export function expectedLocalDateTime(
  year: number,
  monthIndex: number,
  day: number,
  hour: number,
  minute: number,
  second: number
): string {
  const period = hour < 12 ? "AM" : "PM";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${MONTH_NAMES[monthIndex]} ${day}, ${year}, ${hour12}:${pad(minute)}:${pad(second)} ${period}`;
}

/**
 * Same as expectedLocalDateTime, but reads the local-time components straight off a Date/
 * parseable value via the plain Date getters (not Intl), for use with values that come in as
 * a UTC-anchored ISO string or epoch rather than fixed local components.
 */
export function expectedLocalDateTimeFromInput(value: string | number | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return expectedLocalDateTime(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    date.getHours(),
    date.getMinutes(),
    date.getSeconds()
  );
}
