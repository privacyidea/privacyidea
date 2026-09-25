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
import { reservedNames } from "./reserved-names.utils";

describe("reservedNames", () => {
  function nameForm(name: string) {
    return TestBed.runInInjectionContext(() =>
      form(signal({ name }), (f) => {
        reservedNames(f.name, ["test", "."]);
      })
    );
  }

  it.each(["test", "."])("rejects the reserved name %p", (name) => {
    const f = nameForm(name);
    expect(f.name().errors().some((e) => e.kind === "reservedName")).toBe(true);
    expect(f().valid()).toBe(false);
  });

  it.each(["tester", "Test", "...", ""])("accepts the name %p", (name) => {
    const f = nameForm(name);
    expect(f.name().errors()).toEqual([]);
    expect(f().valid()).toBe(true);
  });
});
