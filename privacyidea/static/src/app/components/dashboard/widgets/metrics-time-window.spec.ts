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
import { DEFAULT_METRICS_TIME_WINDOW, METRICS_TIME_WINDOWS } from "./metrics-time-window";

// What lib/metrics.py keeps: rows are dropped once they are older than RETENTION_SECONDS, which the metrics cleanup
// job defaults to as well. A window past it would be a promise the store cannot keep - the widget would show the
// hours that happen to be left rather than the span its label names.
const RETENTION_SECONDS = 24 * 3600;

describe("metrics time windows", () => {
  it("should offer distinct ids", () => {
    const ids = METRICS_TIME_WINDOWS.map((window) => window.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("should ask for no more than the metric store keeps", () => {
    for (const window of METRICS_TIME_WINDOWS) {
      expect(window.seconds).toBeGreaterThan(0);
      expect(window.seconds).toBeLessThanOrEqual(RETENTION_SECONDS);
    }
  });

  it("should open on the hour", () => {
    expect(DEFAULT_METRICS_TIME_WINDOW.id).toBe("1h");
    expect(DEFAULT_METRICS_TIME_WINDOW.seconds).toBe(3600);
  });

  it("should offer the default among its windows, so the picker can show it as selected", () => {
    expect(METRICS_TIME_WINDOWS).toContain(DEFAULT_METRICS_TIME_WINDOW);
  });
});
