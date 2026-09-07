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
import { activityRangeById, bucketsAreCalendarDays } from "@components/dashboard/widgets/activity-range";

const MONTH = activityRangeById("30d")!;
const DAY = activityRangeById("24h")!;

// The offset of a moment is all the predicate reads of a window's end, and an offset that differs between the ends is
// what a zone change looks like from there. Standing in for a Date keeps the suite off any particular zone - the
// machine running it may be in one that never changes its clocks, or in one that changes them on a different date.
function moment(offsetMinutes: number): Date {
  return { getTimezoneOffset: () => offsetMinutes } as unknown as Date;
}

describe("bucketsAreCalendarDays", () => {
  it("lets a day bucket be named by its date while the window keeps one offset", () => {
    expect(bucketsAreCalendarDays(MONTH, moment(-60), moment(-60))).toBe(true);
  });

  it("gives up the date when the clocks change inside the window", () => {
    // The endpoint cuts the window into equal parts, so every bucket after the change starts an hour off the midnight
    // it would be named by: two bars would carry the same date and none the day between them.
    expect(bucketsAreCalendarDays(MONTH, moment(-60), moment(-120))).toBe(false);
    expect(bucketsAreCalendarDays(MONTH, moment(-120), moment(-60))).toBe(false);
  });

  it("never claims a calendar day for a range that is not cut into days", () => {
    // This window is measured back from now, so its buckets sit where the request was made rather than on midnight.
    expect(bucketsAreCalendarDays(DAY, moment(-60), moment(-60))).toBe(false);
  });
});
