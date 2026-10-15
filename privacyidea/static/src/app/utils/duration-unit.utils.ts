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

// A duration is always stored in seconds; the unit only changes how it is entered and displayed.
export type DurationUnit = "seconds" | "minutes" | "hours";

export const DURATION_UNITS: readonly DurationUnit[] = ["seconds", "minutes", "hours"];

export const DURATION_UNIT_FACTORS: Record<DurationUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600
};

// The coarsest unit that divides the seconds evenly, so a stored duration shows as e.g. "10 minutes" rather than
// "600 seconds". The unit the admin entered it in is not stored, so this is the most readable whole-number one. Zero,
// which every unit divides, stays in seconds - in hours, the next number typed would be read as hours.
export function largestWholeDurationUnit(seconds: number): DurationUnit {
  if (seconds === 0) {
    return "seconds";
  }
  if (seconds % DURATION_UNIT_FACTORS.hours === 0) {
    return "hours";
  }
  if (seconds % DURATION_UNIT_FACTORS.minutes === 0) {
    return "minutes";
  }
  return "seconds";
}
