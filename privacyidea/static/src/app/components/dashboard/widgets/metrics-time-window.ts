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
 * The time windows the metric-backed dashboard widgets - resolver timing and notification delivery - can be read
 * over, shared so both present the same vocabulary and store the same ids.
 *
 * Deliberately not the ACTIVITY_RANGES the chart widgets share: a range there is a window *and* a bucket count, which
 * these endpoints do not take, and a day is the most the metric store holds.
 */
export interface MetricsTimeWindow {
  // Names the window in the picker and in the stored widget options, so neither depends on the translated label.
  id: string;
  label: string;
  // What the endpoints take: the window runs back this far from the moment of the request.
  seconds: number;
}

const SECONDS_PER_HOUR = 3600;

// An hour is short enough that a slow resolver shows up as slow rather than being averaged away by the hours around it.
export const DEFAULT_METRICS_TIME_WINDOW: MetricsTimeWindow = {
  id: "1h",
  label: $localize`1 h`,
  seconds: SECONDS_PER_HOUR
};

export const METRICS_TIME_WINDOWS: readonly MetricsTimeWindow[] = [
  DEFAULT_METRICS_TIME_WINDOW,
  { id: "6h", label: $localize`6 h`, seconds: 6 * SECONDS_PER_HOUR },
  { id: "24h", label: $localize`24 h`, seconds: 24 * SECONDS_PER_HOUR }
];
