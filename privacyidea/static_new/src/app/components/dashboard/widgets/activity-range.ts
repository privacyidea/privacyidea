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
 * The time ranges a dashboard chart can be read over, shared by the widgets that offer them so the two present the
 * same vocabulary: the same four labels, the same windows behind them, and the same bucket sizes.
 *
 * A range is a *window plus a bucket size*, not merely a span: what a preset means is "these buckets over this
 * window", and both are what a caller has to send to the aggregating endpoints.
 */
const MS_PER_MINUTE = 60_000;
const MS_PER_HOUR = 60 * MS_PER_MINUTE;
const MS_PER_DAY = 24 * MS_PER_HOUR;

// The window one preset asks the endpoint for, and how many buckets it wants it cut into.
export interface ActivityWindow {
  start: Date;
  end: Date;
  bins: number;
}

export interface ActivityRange {
  // Names the range in the toggle group and in the store key, so neither depends on the translated label.
  id: string;
  label: string;
  // The window to ask for, given the present. Every range cuts it into buckets of a round unit of time - five
  // minutes, an hour, six hours, a day - rather than into an arbitrary slice of itself.
  window: (now: Date) => ActivityWindow;
  // Whether a bucket is one whole calendar day, which is what lets a bar be named by its date rather than by the
  // span it runs over.
  wholeDayBuckets: boolean;
}

// Local midnight, `days` days back. Stepped by calendar date rather than by 24-hour blocks, so a daylight-saving
// change in between does not leave the window opening at 23:00 or 01:00.
function midnightDaysAgo(now: Date, days: number): Date {
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - days);
  return start;
}

// A window that simply runs back from now. This is how "the last hour" and "the last 24 hours" are read: the window's
// own edges are the round thing about it, and every bucket in it is a bucket that has fully happened.
function rollingWindow(spanMs: number, bucketMs: number): (now: Date) => ActivityWindow {
  return (now) => ({
    start: new Date(now.getTime() - spanMs),
    end: now,
    bins: spanMs / bucketMs
  });
}

// A window over whole calendar days: it opens at midnight `days` days back and closes at the end of the bucket now
// falls in, so a bucket never straddles two days and a day is always the same number of buckets - four for the week,
// one for the month. Today is in the window as far as it has got, its last bucket still filling, which is what makes
// the newest attempts show up without waiting for the day to end.
//
// The buckets are an even division of the window, which is all the endpoint offers, so a daylight-saving change
// inside one shifts the buckets after it an hour off the midnights they started on.
function dailyWindow(days: number, bucketMs: number): (now: Date) => ActivityWindow {
  return (now) => {
    const start = midnightDaysAgo(now, days);
    // Rounded up rather than down: the bucket now falls in is the one holding the most recent attempts, and ending
    // the window at the last closed bucket would leave them out until it closed.
    const bins = Math.max(1, Math.ceil((now.getTime() - start.getTime()) / bucketMs));
    return { start, end: new Date(start.getTime() + bins * bucketMs), bins };
  };
}

export const ACTIVITY_RANGES: readonly ActivityRange[] = [
  { id: "1h", label: $localize`1 h`, window: rollingWindow(MS_PER_HOUR, 5 * MS_PER_MINUTE), wholeDayBuckets: false },
  { id: "24h", label: $localize`24 h`, window: rollingWindow(MS_PER_DAY, MS_PER_HOUR), wholeDayBuckets: false },
  { id: "7d", label: $localize`7 d`, window: dailyWindow(7, 6 * MS_PER_HOUR), wholeDayBuckets: false },
  { id: "30d", label: $localize`30 d`, window: dailyWindow(30, MS_PER_DAY), wholeDayBuckets: true }
];
