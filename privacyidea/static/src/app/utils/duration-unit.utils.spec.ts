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
import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { form } from "@angular/forms/signals";
import {
  DurationFormModel,
  durationRules,
  durationToSeconds,
  isPositiveWholeNumber,
  largestWholeDurationUnit,
  POSITIVE_INTEGER_ERROR,
  selectedDurationSeconds
} from "./duration-unit.utils";

describe("largestWholeDurationUnit", () => {
  it("picks hours for a whole number of hours", () => {
    expect(largestWholeDurationUnit(7200)).toBe("hours");
  });

  it("picks minutes for a whole number of minutes that is not a whole number of hours", () => {
    expect(largestWholeDurationUnit(5400)).toBe("minutes");
  });

  it("picks seconds when no coarser unit divides evenly", () => {
    expect(largestWholeDurationUnit(90)).toBe("seconds");
  });

  it("picks seconds for zero, which every unit divides", () => {
    expect(largestWholeDurationUnit(0)).toBe("seconds");
  });
});

describe("isPositiveWholeNumber", () => {
  it.each([1, 2, 3600])("accepts %s", (value) => {
    expect(isPositiveWholeNumber(value)).toBe(true);
  });

  it.each([null, 0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY])("rejects %s", (value) => {
    expect(isPositiveWholeNumber(value)).toBe(false);
  });
});

describe("durationToSeconds", () => {
  it("multiplies the number by the factor of the unit", () => {
    expect(durationToSeconds(5, "seconds")).toBe(5);
    expect(durationToSeconds(2, "minutes")).toBe(120);
    expect(durationToSeconds(2, "hours")).toBe(7200);
  });

  it("returns null when the number is not a positive whole number", () => {
    expect(durationToSeconds(null, "minutes")).toBeNull();
    expect(durationToSeconds(0, "minutes")).toBeNull();
    expect(durationToSeconds(1.5, "minutes")).toBeNull();
  });
});

describe("selectedDurationSeconds", () => {
  it("is null for a permanent mode, whatever was entered", () => {
    expect(selectedDurationSeconds({ mode: "permanent", durationInput: 5, durationUnit: "hours" })).toBeNull();
  });

  it("converts the entered duration for a timed mode", () => {
    expect(selectedDurationSeconds({ mode: "timed", durationInput: 5, durationUnit: "minutes" })).toBe(300);
  });

  it("is null for a timed mode without a valid duration", () => {
    expect(selectedDurationSeconds({ mode: "timed", durationInput: null, durationUnit: "minutes" })).toBeNull();
  });
});

describe("durationRules", () => {
  const setup = (initial: Partial<DurationFormModel> = {}) => {
    const model = signal<DurationFormModel>({
      mode: "permanent",
      durationInput: null,
      durationUnit: "minutes",
      ...initial
    });
    const f = TestBed.runInInjectionContext(() =>
      form(model, (p) => durationRules(p.mode, p.durationInput, p.durationUnit))
    );
    const kinds = () =>
      f
        .durationInput()
        .errors()
        .map((e) => e.kind);
    return { model, f, kinds };
  };

  it("disables the duration and the unit while the mode is permanent, and enables them for timed", () => {
    const { model, f } = setup();
    expect(f.durationInput().disabled()).toBe(true);
    expect(f.durationUnit().disabled()).toBe(true);

    model.update((m) => ({ ...m, mode: "timed" }));

    expect(f.durationInput().disabled()).toBe(false);
    expect(f.durationUnit().disabled()).toBe(false);
  });

  it("counts an empty duration as valid while permanent", () => {
    const { f } = setup();
    expect(f().valid()).toBe(true);
  });

  it("requires a duration for a timed mode", () => {
    const { f, kinds } = setup({ mode: "timed" });
    expect(kinds()).toEqual(["required"]);
    expect(f().valid()).toBe(false);
  });

  it.each([0, -1, 2.5])("rejects the timed duration %s", (durationInput) => {
    const { kinds } = setup({ mode: "timed", durationInput });
    expect(kinds()).toEqual([POSITIVE_INTEGER_ERROR]);
  });

  it("accepts a positive whole timed duration", () => {
    const { f, kinds } = setup({ mode: "timed", durationInput: 10 });
    expect(kinds()).toEqual([]);
    expect(f().valid()).toBe(true);
  });
});
