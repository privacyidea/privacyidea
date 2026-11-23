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
import { TestBed } from "@angular/core/testing";
import { provideNativeDateAdapter } from "@angular/material/core";
import { DateRange } from "@angular/material/datepicker";
import { SortedRangeSelectionStrategy } from "./sorted-range-selection-strategy";

describe("SortedRangeSelectionStrategy", () => {
  let strategy: SortedRangeSelectionStrategy<Date>;
  const june2 = new Date(2026, 5, 2);
  const june5 = new Date(2026, 5, 5);

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideNativeDateAdapter(), SortedRangeSelectionStrategy] });
    strategy = TestBed.inject(SortedRangeSelectionStrategy<Date>);
  });

  it("starts a range on the first pick", () => {
    expect(strategy.selectionFinished(june5, new DateRange<Date>(null, null))).toEqual(new DateRange(june5, null));
  });

  it("ends the range on a later second pick", () => {
    expect(strategy.selectionFinished(june5, new DateRange<Date>(june2, null))).toEqual(new DateRange(june2, june5));
  });

  it("makes an earlier second pick the start and the first pick the end", () => {
    expect(strategy.selectionFinished(june2, new DateRange<Date>(june5, null))).toEqual(new DateRange(june2, june5));
  });

  it("starts a new range on a pick once both ends are set", () => {
    expect(strategy.selectionFinished(june5, new DateRange<Date>(june2, june5))).toEqual(new DateRange(june5, null));
  });

  it("previews the sorted range while an end is awaited, and nothing otherwise", () => {
    expect(strategy.createPreview(june2, new DateRange<Date>(june5, null))).toEqual(new DateRange(june2, june5));
    expect(strategy.createPreview(june2, new DateRange<Date>(june2, june5))).toEqual(new DateRange<Date>(null, null));
  });
});
