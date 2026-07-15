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
import { formatLocalDateTime } from "./date-format.utils";

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

  it("formats a date-only/time-free ISO string (interpreted as local midnight)", () => {
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
