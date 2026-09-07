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
const MS_PER_SECOND = 1_000;
const MS_PER_MINUTE = 60 * MS_PER_SECOND;
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
  // Whether a bucket is *meant* to be one whole calendar day. Whether it is one is a question about the window as
  // well - see bucketsAreCalendarDays, which is what a label has to ask before naming a bar by its date alone.
  dayBuckets: boolean;
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
  return (now) => {
    // Cut to the second, so that every bucket edge is a whole one. The log's time filter names seconds and nothing
    // finer, so an edge carrying milliseconds is an edge no drill-down can ask for: the span it opened the log on
    // would be a fraction beside the bar that was clicked, and the boundary second would belong to both or neither.
    const end = Math.floor(now.getTime() / MS_PER_SECOND) * MS_PER_SECOND;
    return { start: new Date(end - spanMs), end: new Date(end), bins: spanMs / bucketMs };
  };
}

// A window over whole calendar days: it opens at midnight `days` days back and closes at the end of the bucket now
// falls in, so a bucket never straddles two days and a day is always the same number of buckets - four for the week,
// one for the month. Today is in the window as far as it has got, its last bucket still filling, which is what makes
// the newest attempts show up without waiting for the day to end.
//
// The buckets are an even division of the window, which is all the endpoint offers, so a daylight-saving change
// inside the window shifts every bucket after it an hour off the midnight it should have started on. The window
// stays whole days either way; what stops holding is that a bucket *is* one, which is why the labels ask
// bucketsAreCalendarDays rather than trusting the flag on their own.
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
  { id: "1h", label: $localize`1 h`, window: rollingWindow(MS_PER_HOUR, 5 * MS_PER_MINUTE), dayBuckets: false },
  { id: "24h", label: $localize`24 h`, window: rollingWindow(MS_PER_DAY, MS_PER_HOUR), dayBuckets: false },
  { id: "7d", label: $localize`7 d`, window: dailyWindow(7, 6 * MS_PER_HOUR), dayBuckets: false },
  { id: "30d", label: $localize`30 d`, window: dailyWindow(30, MS_PER_DAY), dayBuckets: true }
];

// A bucket's exclusive end, said the way the authentication log's own filter says it. The log takes both bounds
// inclusively and names whole seconds, while a bucket ends where the next one begins, so the last second the bucket
// still holds is the same span in that vocabulary. Without the step back, an entry timestamped exactly on the edge
// would be listed under the bar that did not count it - and edges are whole seconds, which is where every entry sits
// on a backend whose timestamp column keeps no fraction of one.
//
// Only for an edge that *is* the next bucket's start: the window's own end is not one, the endpoint closing the last
// bucket on it rather than past it, so that bound is already inclusive and is passed as it stands.
export function inclusiveBucketEnd(exclusiveEndMs: number): number {
  return exclusiveEndMs - MS_PER_SECOND;
}

// Whether the buckets of the window between *windowStart* and *windowEnd* really are calendar days, which is what
// lets a bar carry a date and no time. The endpoint cuts a window into equal parts, so a day bucket is 24 hours of
// absolute time - a calendar day right up until the clocks change, after which every later bucket starts an hour off
// the midnight whose date it would be named by. Two bars would then carry the same date and none the day between
// them, so the labels fall back to naming the span a bucket actually runs over.
//
// The ends of the window answer for all of it: the two changes in a year are seven months apart, so a window this
// chart can ask for holds at most one, and equal offsets at the ends mean no change in between.
export function bucketsAreCalendarDays(range: ActivityRange, windowStart: Date, windowEnd: Date): boolean {
  return range.dayBuckets && windowStart.getTimezoneOffset() === windowEnd.getTimezoneOffset();
}

// Looked up by id rather than by position, so reordering the table for the toggle group cannot silently change what a
// widget opens on or what a stored id resolves to.
export function activityRangeById(id: string): ActivityRange | undefined {
  return ACTIVITY_RANGES.find((range) => range.id === id);
}

// What a chart opens on. A day is the span a dashboard reader wants first: long enough to cover a night's activity,
// short enough that a bucket is an hour.
export const DEFAULT_ACTIVITY_RANGE: ActivityRange = activityRangeById("24h") ?? ACTIVITY_RANGES[0];
