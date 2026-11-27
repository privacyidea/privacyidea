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

import { expectedLocalDateTime } from "@testing/expected-local-date-time";
import {
  atLocalTimeIso,
  formatLocalDateTime,
  hasNoTimeZoneOffset,
  parseFilterEndTimestamp,
  parseFilterTimestamp
} from "./date-format.utils";

describe("formatLocalDateTime", () => {
  it("returns an empty string for null, undefined or empty input", () => {
    expect(formatLocalDateTime(null)).toBe("");
    expect(formatLocalDateTime(undefined)).toBe("");
    expect(formatLocalDateTime("")).toBe("");
  });

  it("returns the raw value when the input is not a parseable date", () => {
    expect(formatLocalDateTime("not-a-date")).toBe("not-a-date");
  });

  it("formats a local Date instance into 'MMM d, yyyy, h:mm:ss AM/PM'", () => {
    const date = new Date(2026, 6, 1, 10, 30, 45);
    expect(formatLocalDateTime(date)).toBe(expectedLocalDateTime(2026, 6, 1, 10, 30, 45));
  });

  it("formats an epoch number the same way as the equivalent Date", () => {
    const epoch = new Date(2026, 6, 1, 10, 30, 45).getTime();
    expect(formatLocalDateTime(epoch)).toBe(expectedLocalDateTime(2026, 6, 1, 10, 30, 45));
  });

  it("formats an ISO string without a UTC offset (interpreted as local time)", () => {
    expect(formatLocalDateTime("2026-01-05T00:05:09")).toBe(expectedLocalDateTime(2026, 0, 5, 0, 5, 9));
  });

  it("converts noon (12:00) to '12:00:00 PM', not '0:00:00 PM'", () => {
    const date = new Date(2026, 0, 1, 12, 0, 0);
    expect(formatLocalDateTime(date)).toBe(expectedLocalDateTime(2026, 0, 1, 12, 0, 0));
  });

  it("converts midnight (00:00) to '12:00:00 AM', not '0:00:00 AM'", () => {
    const date = new Date(2026, 0, 1, 0, 0, 0);
    expect(formatLocalDateTime(date)).toBe(expectedLocalDateTime(2026, 0, 1, 0, 0, 0));
  });

  it("formats a space-separated server timestamp the same as its 'T'-separated equivalent", () => {
    expect(formatLocalDateTime("2026-01-05 10:30:45")).toBe(formatLocalDateTime("2026-01-05T10:30:45"));
  });

  it("formats a timestamp with microsecond precision instead of returning the raw value", () => {
    expect(formatLocalDateTime("2026-01-05T10:30:45.123456")).toBe(formatLocalDateTime("2026-01-05T10:30:45.123"));
  });

  it("formats a space-separated timestamp with microsecond precision and a UTC offset", () => {
    expect(formatLocalDateTime("2026-01-05 10:30:45.123456+0200")).toBe(
      formatLocalDateTime("2026-01-05T10:30:45.123+02:00")
    );
  });

  it("formats a positive UTC offset without a colon the same as its colon equivalent", () => {
    expect(formatLocalDateTime("2026-01-05T10:30:45+0200")).toBe(formatLocalDateTime("2026-01-05T10:30:45+02:00"));
  });

  it("formats a negative UTC offset without a colon the same as its colon equivalent", () => {
    expect(formatLocalDateTime("2026-01-05T10:30:45-0500")).toBe(formatLocalDateTime("2026-01-05T10:30:45-05:00"));
  });

  it("formats a 'Z' offset the same as its explicit +00:00 equivalent", () => {
    expect(formatLocalDateTime("2026-01-05T10:30:45Z")).toBe(formatLocalDateTime("2026-01-05T10:30:45+00:00"));
  });

  it("treats a bare date (no time part) as local midnight, not UTC midnight", () => {
    expect(formatLocalDateTime("2026-01-31")).toBe(expectedLocalDateTime(2026, 0, 31, 0, 0, 0));
  });

  it("does not shift a bare date to the previous day the way UTC-midnight parsing would west of UTC", () => {
    expect(formatLocalDateTime("2026-01-31")).not.toBe(expectedLocalDateTime(2026, 0, 30, 23, 0, 0));
  });

  it("returns the raw value for a bare date with an invalid calendar day instead of throwing", () => {
    expect(formatLocalDateTime("2026-13-45")).toBe("2026-13-45");
  });

  it("returns the raw value for a non-date string unaffected by the offset/date-only handling", () => {
    expect(formatLocalDateTime("not-a-date")).toBe("not-a-date");
  });
});

describe("atLocalTimeIso", () => {
  it("sets the local wall-clock time at second 0 on the date's local day", () => {
    expect(atLocalTimeIso(new Date(2026, 8, 24, 13, 0), "08:30")).toBe(
      new Date(2026, 8, 24, 8, 30, 0, 0).toISOString()
    );
    expect(atLocalTimeIso(new Date(2026, 8, 24), "17:15")).toBe(new Date(2026, 8, 24, 17, 15, 0, 0).toISOString());
  });

  it("returns null for an empty or malformed time", () => {
    expect(atLocalTimeIso(new Date(2026, 8, 24), "")).toBeNull();
    expect(atLocalTimeIso(new Date(2026, 8, 24), "25:00")).toBeNull();
    expect(atLocalTimeIso(new Date(2026, 8, 24), "8:3")).toBeNull();
  });
});

describe("parseFilterTimestamp", () => {
  // Expectations are built with the local Date constructor, so they hold in any zone. In a zone away from UTC
  // (as on a developer machine) a bound read as UTC instead of local fails them.
  it("reads every ISO 8601 form a bound may be typed in as the instant it names", () => {
    // Local wall-clock time as ISO, built with the local Date constructor so it holds in any zone. Month is 1-based.
    const local = (year: number, month: number, day = 1, hour = 0, minute = 0, second = 0, ms = 0): string =>
      new Date(year, month - 1, day, hour, minute, second, ms).toISOString();
    const expected: Record<string, string> = {
      // A date alone is the start of that local period, local midnight and not UTC midnight
      "2026": local(2026, 1),
      "2026-11": local(2026, 11),
      "2026-11-05": local(2026, 11, 5),
      // A date and time without an offset is the viewer's local time, with a space or a T, with or without seconds
      "2026-11-05 10:00:00": local(2026, 11, 5, 10),
      "2026-11-05 10:00": local(2026, 11, 5, 10),
      "2026-11-05T10:00:00": local(2026, 11, 5, 10),
      "2026-11-05T10:00": local(2026, 11, 5, 10),
      // A valid leap day is read, unlike 2026-02-29
      "2028-02-29 10:00": local(2028, 2, 29, 10),
      // Fractions of a second, also longer than the 3 digits new Date() takes
      "2026-11-05 10:00:00.123": local(2026, 11, 5, 10, 0, 0, 123),
      "2026-11-05T10:00:00.123456Z": "2026-11-05T10:00:00.123Z",
      // Z or an offset names the instant, with or without a colon and with or without a space before it (the filter
      // text mirrors "yyyy-MM-dd HH:mm:ss +01:00")
      "2026-11-05T10:00:00Z": "2026-11-05T10:00:00.000Z",
      "2026-11-05T10:00 Z": "2026-11-05T10:00:00.000Z",
      "2026-11-05 10:00:00 +01:00": "2026-11-05T09:00:00.000Z",
      "2026-11-05T10:00+01:00": "2026-11-05T09:00:00.000Z",
      "2026-11-05T10:00:00+0100": "2026-11-05T09:00:00.000Z",
      "2026-11-05 10:00 +0100": "2026-11-05T09:00:00.000Z",
      "2026-11-05T10:00:00 -05:00": "2026-11-05T15:00:00.000Z",
      // A lowercase t or z reads as its uppercase form
      "2026-11-05t10:00": local(2026, 11, 5, 10),
      "2026-11-05t10:00:00z": "2026-11-05T10:00:00.000Z",
      "2026-11-05 10:00:00 z": "2026-11-05T10:00:00.000Z"
    };
    for (const [value, iso] of Object.entries(expected)) {
      expect({ value, parsed: parseFilterTimestamp(value) }).toEqual({ value, parsed: iso });
    }
  });

  it("returns null for text that is no ISO 8601 date and time instead of letting the browser guess or roll it over", () => {
    const values = [
      // German date with dots (the browser reads M.D.Y)
      "5.11.2026",
      "05.11.2026",
      "5.11.2026 10:00",
      // Slashes
      "11/5/2026",
      "5/11/2026",
      "2026/11/05",
      // English month or weekday names
      "Nov 5",
      "5 Nov 2026",
      "November 5, 2026",
      "Thu Nov 05 2026",
      // Free text and bare numbers
      "foo 1",
      "abc 2026",
      "today",
      "1",
      "12",
      // Impossible days with a time (would roll over)
      "2026-02-31 10:00",
      "2026-11-31T10:00",
      "2026-02-30T10:00:00Z",
      "2026-02-29 10:00",
      // ISO with trailing text or a fraction without seconds
      "2026-11-05T10:00 foo",
      "2026-11-05T10:00.123",
      // Empty, malformed or impossible date alone
      "",
      "2026-11-05 10:0x",
      "2026-13",
      "2026-02-31"
    ];
    for (const value of values) {
      expect({ value, parsed: parseFilterTimestamp(value) }).toEqual({ value, parsed: null });
    }
    expect(parseFilterEndTimestamp("5.11.2026")).toBeNull();
  });
});

describe("parseFilterEndTimestamp", () => {
  it("reads a typed end that is only a date as the end of that local day", () => {
    expect(parseFilterEndTimestamp("2026-11-05")).toBe(new Date(2026, 10, 5, 23, 59, 59, 0).toISOString());
  });

  it("reads a typed month or year as the end of its last local day", () => {
    expect(parseFilterEndTimestamp("2026-11")).toBe(new Date(2026, 10, 30, 23, 59, 59, 0).toISOString());
    expect(parseFilterEndTimestamp("2026-02")).toBe(new Date(2026, 1, 28, 23, 59, 59, 0).toISOString());
    expect(parseFilterEndTimestamp("2026")).toBe(new Date(2026, 11, 31, 23, 59, 59, 0).toISOString());
  });

  it("reads an end with a time or an offset as parseFilterTimestamp does", () => {
    expect(parseFilterEndTimestamp("2026-11-05 10:00:00")).toBe(new Date(2026, 10, 5, 10, 0, 0, 0).toISOString());
    expect(parseFilterEndTimestamp("2026-11-05T10:00:00Z")).toBe("2026-11-05T10:00:00.000Z");
    expect(parseFilterEndTimestamp("2026-13")).toBeNull();
    expect(parseFilterEndTimestamp("")).toBeNull();
  });
});

describe("hasNoTimeZoneOffset", () => {
  it.each(["2026-11-05T10:00:00.123456", "2026-11-05T10:00:00"])("is true for %p, an offset-less timestamp", (value) => {
    expect(hasNoTimeZoneOffset(value)).toBe(true);
  });

  it.each([
    "2026-11-05T10:00:00.123456+00:00",
    "2026-11-05T10:00:00+01:00",
    "2026-11-05T10:00:00Z",
    null,
    undefined,
    "",
    "foo"
  ])("is false for %p", (value) => {
    expect(hasNoTimeZoneOffset(value)).toBe(false);
  });
});
