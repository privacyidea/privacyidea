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
import { largestWholeDurationUnit } from "./duration-unit.utils";

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
