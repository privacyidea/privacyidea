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

import { disabled, required, SchemaPath, validate } from "@angular/forms/signals";

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

// Error kind of a duration that is a number but not a whole number greater than zero.
export const POSITIVE_INTEGER_ERROR = "positiveInteger";

// Whether `value` is a whole number greater than zero, the only kind of duration the backend accepts.
export function isPositiveWholeNumber(value: number | null): value is number {
  return value !== null && Number.isInteger(value) && value > 0;
}

// The entered duration in seconds, or null when it is not a positive whole number.
export function durationToSeconds(value: number | null, unit: DurationUnit): number | null {
  return isPositiveWholeNumber(value) ? value * DURATION_UNIT_FACTORS[unit] : null;
}

// Whether a lock or block expires after a duration or stays until an administrator lifts it.
export type DurationMode = "permanent" | "timed";

// The state of the permanent/timed duration controls. The unit applies to the entered number.
export interface DurationFormModel {
  mode: DurationMode;
  durationInput: number | null;
  durationUnit: DurationUnit;
}

// The seconds a lock or block lasts: null while it is permanent or when the entered duration is not valid.
export function selectedDurationSeconds(model: DurationFormModel): number | null {
  return model.mode === "permanent" ? null : durationToSeconds(model.durationInput, model.durationUnit);
}

// The rules of the permanent/timed duration controls shared by the user lock and the blocklist block dialog.
// Both controls are disabled while the mode is permanent, so they stay in the layout without blocking the form.
// A timed duration is required and has to be a positive whole number.
export function durationRules(
  mode: SchemaPath<DurationMode>,
  durationInput: SchemaPath<number | null>,
  durationUnit: SchemaPath<DurationUnit>
): void {
  disabled(durationInput, ({ valueOf }) => valueOf(mode) === "permanent");
  disabled(durationUnit, ({ valueOf }) => valueOf(mode) === "permanent");
  required(durationInput);
  validate(durationInput, ({ value }) =>
    value() === null || isPositiveWholeNumber(value()) ? [] : [{ kind: POSITIVE_INTEGER_ERROR }]
  );
}
