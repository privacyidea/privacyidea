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

// Matches server-supplied "YYYY-MM-DD HH:mm:ss[.fraction][offset]" timestamps that use a
// space instead of "T", or a fractional-seconds part longer than the 3 digits (milliseconds)
// the Date Time String Format allows. Both are only reliably parsed by new Date() on some
// engines, so normalize to a spec-conformant ISO string before parsing.
const LOOSE_ISO_DATE_TIME_REGEX = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$/;

function normalizeDateTimeString(value: string): string {
  const match = LOOSE_ISO_DATE_TIME_REGEX.exec(value);
  if (!match) return value;
  const [, datePart, timePart, fraction, offset] = match;
  const milliseconds = fraction ? `.${fraction.slice(1, 4).padEnd(3, "0")}` : "";
  return `${datePart}T${timePart}${milliseconds}${offset ?? ""}`;
}

let localDateTimeFormatter: Intl.DateTimeFormat | undefined;
function getLocalDateTimeFormatter(): Intl.DateTimeFormat {
  localDateTimeFormatter ??= new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" });
  return localDateTimeFormatter;
}

export function formatLocalDateTime(value: string | number | Date | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const normalized = typeof value === "string" ? normalizeDateTimeString(value) : value;
  const date = normalized instanceof Date ? normalized : new Date(normalized);
  if (Number.isNaN(date.getTime())) return String(value);
  return getLocalDateTimeFormatter().format(date);
}
