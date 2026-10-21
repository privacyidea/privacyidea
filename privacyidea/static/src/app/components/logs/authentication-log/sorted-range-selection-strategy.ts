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
import { inject, Injectable } from "@angular/core";
import { DateAdapter } from "@angular/material/core";
import { DateRange, MatDateRangeSelectionStrategy } from "@angular/material/datepicker";

// Material's default range strategy starts over on a second pick before the range's start. This one keeps both picks:
// the earlier day is the start and the later one the end, and the hover preview shows the same.
@Injectable()
export class SortedRangeSelectionStrategy<D> implements MatDateRangeSelectionStrategy<D> {
  private readonly dateAdapter = inject<DateAdapter<D>>(DateAdapter);

  selectionFinished(date: D | null, currentRange: DateRange<D>): DateRange<D> {
    if (!this.awaitsEnd(currentRange) || date == null) {
      return new DateRange<D>(date, null);
    }
    return this.sorted(currentRange.start!, date);
  }

  createPreview(activeDate: D | null, currentRange: DateRange<D>): DateRange<D> {
    if (!this.awaitsEnd(currentRange) || activeDate == null) {
      return new DateRange<D>(null, null);
    }
    return this.sorted(currentRange.start!, activeDate);
  }

  private awaitsEnd(range: DateRange<D>): boolean {
    return range.start != null && range.end == null;
  }

  private sorted(first: D, second: D): DateRange<D> {
    return this.dateAdapter.compareDate(first, second) <= 0
      ? new DateRange<D>(first, second)
      : new DateRange<D>(second, first);
  }
}
