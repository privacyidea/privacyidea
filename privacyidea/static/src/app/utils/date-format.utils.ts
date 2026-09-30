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

import { formatDate } from "@angular/common";

// Matches server-supplied "YYYY-MM-DD HH:mm:ss[.fraction][offset]" timestamps that use a
// space instead of "T", a fractional-seconds part longer than the 3 digits (milliseconds)
// the Date Time String Format allows, or an offset without a colon. All three are only
// reliably parsed by new Date() on some engines, so normalize to a spec-conformant ISO
// string before parsing.
const LOOSE_ISO_DATE_TIME_REGEX = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$/;
const DATE_ONLY_REGEX = /^\d{4}-\d{2}-\d{2}$/;

// Normalizes a server timestamp to a spec-conformant ISO string new Date() parses consistently,
// and treats a bare date as local midnight instead of JavaScript's UTC-midnight default.
export function normalizeDateTimeString(value: string): string {
  if (DATE_ONLY_REGEX.test(value)) return `${value}T00:00:00`;
  const match = LOOSE_ISO_DATE_TIME_REGEX.exec(value);
  if (!match) return value;
  const [, datePart, timePart, fraction, offset] = match;
  const milliseconds = fraction ? `.${fraction.slice(1, 4).padEnd(3, "0")}` : "";
  const normalizedOffset = offset && offset.length === 5 ? `${offset.slice(0, 3)}:${offset.slice(3)}` : offset;
  return `${datePart}T${timePart}${milliseconds}${normalizedOffset ?? ""}`;
}

const localFormatters = new Map<string, Intl.DateTimeFormat>();
function getLocalFormatter(options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = JSON.stringify(options);
  let formatter = localFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(undefined, options);
    localFormatters.set(key, formatter);
  }
  return formatter;
}

function formatLocal(value: string | number | Date | null | undefined, options: Intl.DateTimeFormatOptions): string {
  if (value === null || value === undefined || value === "") return "";
  const normalized = typeof value === "string" ? normalizeDateTimeString(value) : value;
  const date = normalized instanceof Date ? normalized : new Date(normalized);
  if (Number.isNaN(date.getTime())) return String(value);
  return getLocalFormatter(options).format(date);
}

export function formatLocalDateTime(value: string | number | Date | null | undefined): string {
  return formatLocal(value, { dateStyle: "medium", timeStyle: "medium" });
}

export function formatLocalDate(value: string | number | Date | null | undefined): string {
  return formatLocal(value, { dateStyle: "medium" });
}

export function formatLocalTime(value: string | number | Date | null | undefined): string {
  return formatLocal(value, { timeStyle: "medium" });
}

/**
 * Converts an ISO 8601 string to the human-readable form the authentication log's editable start_time/end_time filter
 * chips carry, e.g. "2026-06-02T10:00:00.000Z" becomes "2026-06-02 10:00:00 +00:00".
 *
 * Shared rather than local to the log page because anything that pre-seeds those chips - the dashboard's activity
 * widget, for one - has to write the exact form the page mirrors back out, or the page reads the chip as an edit.
 */
export function toFilterDisplay(isoString: string): string {
  return formatDate(isoString, "yyyy-MM-dd HH:mm:ss ZZZZZ", "en-US");
}
