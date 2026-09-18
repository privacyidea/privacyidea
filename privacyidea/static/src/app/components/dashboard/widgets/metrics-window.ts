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
 * these endpoints do not take, and its 7 d and 30 d presets ask for more than the metric store holds. A metric row is
 * a five-minute bucket (``WINDOW_SECONDS`` in lib/metrics.py) dropped once it is a day old (``RETENTION_SECONDS``,
 * which the MetricsCleanup task defaults to as well), so a day is the widest window that can be promised.
 */
export interface MetricsWindow {
  // Names the window in the picker and in the stored widget options, so neither depends on the translated label.
  id: string;
  label: string;
  // What the endpoints take: the window runs back this far from the moment of the request.
  seconds: number;
}

const SECONDS_PER_HOUR = 3600;

export const METRICS_WINDOWS: readonly MetricsWindow[] = [
  { id: "1h", label: $localize`1 h`, seconds: SECONDS_PER_HOUR },
  { id: "6h", label: $localize`6 h`, seconds: 6 * SECONDS_PER_HOUR },
  { id: "24h", label: $localize`24 h`, seconds: 24 * SECONDS_PER_HOUR }
];

// Looked up by id rather than by position, so reordering the list for the picker cannot silently change what a widget
// opens on or what a stored id resolves to.
export function metricsWindowById(id: string | undefined): MetricsWindow | undefined {
  return id === undefined ? undefined : METRICS_WINDOWS.find((window) => window.id === id);
}

// What these widgets open on when nothing has been picked. An hour is short enough that a slow resolver shows up as
// slow rather than being averaged away by the hours around it, and the widest window is one menu away.
export const DEFAULT_METRICS_WINDOW: MetricsWindow = metricsWindowById("1h") ?? METRICS_WINDOWS[0];
