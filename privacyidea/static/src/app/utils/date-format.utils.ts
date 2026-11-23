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
 * chips and the halves of the audit log's startdate interval chip carry, e.g. "2026-06-02T10:00:00.000Z" becomes
 * "2026-06-02 10:00:00 +00:00".
 *
 * Shared rather than local to the log page because anything that pre-seeds those chips - the dashboard's activity
 * widget, for one - has to write the exact form the page mirrors back out, or the page reads the chip as an edit.
 */
export function toFilterDisplay(isoString: string): string {
  return formatDate(isoString, "yyyy-MM-dd HH:mm:ss ZZZZZ", "en-US");
}

// A typed date without a time ("2026", "2026-11" or "2026-11-05") as the local period it names, by its first and its
// last day. Undefined when the value is no date alone, null when it names an impossible date: the Date constructor
// rolls an impossible month or day over into the next one, and a typo must not move the bound.
function typedLocalPeriod(value: string): { first: Date; last: Date } | null | undefined {
  const match: RegExpExecArray | null = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(value);
  if (!match) {
    return undefined;
  }
  const [year, month, date]: number[] = [Number(match[1]), Number(match[2] ?? 1), Number(match[3] ?? 1)];
  const first = new Date(year, month - 1, date);
  if (first.getMonth() !== month - 1 || first.getDate() !== date) {
    return null;
  }
  const last: Date = match[3] ? first : match[2] ? new Date(year, month, 0) : new Date(year, 11, 31);
  return { first, last };
}

/**
 * Inverse of toFilterDisplay for the editable time filter chips: parses the mirrored display, plain ISO
 * or a partial typed datetime into an ISO string, returning null for an empty or unparsable value.
 * A value without an offset is the viewer's local time, as everywhere in the WebUI, a date alone included: it is local
 * midnight, where new Date("2026-11-05") would give UTC midnight. A value with Z or an offset names that instant.
 */
export function parseFilterTimestamp(value: string | null | undefined): string | null {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    return null;
  }
  const period = typedLocalPeriod(trimmed);
  if (period !== undefined) {
    return period ? period.first.toISOString() : null;
  }
  // Normalize the mirrored "yyyy-MM-dd HH:mm:ss +00:00" form to ISO (space->T, drop the space before the offset),
  // then fall back to the raw text so plain ISO input still parses.
  for (const candidate of [trimmed.replace(" ", "T").replace(/\s+(?=[+\-Z])/, ""), trimmed]) {
    const date = new Date(candidate);
    if (!isNaN(date.getTime())) {
      return date.toISOString();
    }
  }
  return null;
}

/**
 * parseFilterTimestamp for the end of a range: a typed end that is only a date (a day, a month or a year) includes
 * that whole local period, so it runs to 23:59:59 of its last day, as a day picked in the range picker does. An end
 * with a time or an offset reads as in parseFilterTimestamp.
 */
export function parseFilterEndTimestamp(value: string | null | undefined): string | null {
  const period = typedLocalPeriod((value ?? "").trim());
  if (period !== undefined) {
    return period ? endOfLocalDayIso(period.last) : null;
  }
  return parseFilterTimestamp(value);
}

/**
 * Inclusive bounds of the local day a date falls on, as the ISO strings the time filters expect. The
 * logs render timestamps in the viewer's zone, so a picked or clicked day means that zone's 00:00:00 to 23:59:59.
 */
export function startOfLocalDayIso(date: Date): string {
  const day = new Date(date);
  day.setHours(0, 0, 0, 0);
  return day.toISOString();
}

export function endOfLocalDayIso(date: Date): string {
  const day = new Date(date);
  day.setHours(23, 59, 59, 0);
  return day.toISOString();
}

/**
 * The local day a date falls on at a wall-clock time given as "HH:mm" (as formatClockTime of the clock dial gives it),
 * at second 0, as an ISO string. Null when the time is empty or malformed.
 */
export function atLocalTimeIso(date: Date, time: string): string | null {
  const match = /^([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$/.exec(time);
  if (!match) {
    return null;
  }
  const day = new Date(date);
  day.setHours(Number(match[1]), Number(match[2]), 0, 0);
  return day.toISOString();
}
