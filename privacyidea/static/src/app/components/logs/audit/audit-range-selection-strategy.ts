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
import { Injectable } from "@angular/core";
import { DateAdapter } from "@angular/material/core";
import { DateRange, DefaultMatCalendarRangeStrategy } from "@angular/material/datepicker";

/**
 * Takes over the day clicks while `active()`: `dayClick` decides the selection, `event` is the event on the cell. A
 * null date is the month view aborting a half-picked range on Escape.
 */
export interface AuditDayClickInterceptor {
  active(): boolean;
  dayClick(date: Date | null, event: Event | undefined): DateRange<Date>;
}

/**
 * The stock range strategy, with a hook for the time mode of the audit range picker: while the interceptor is active,
 * every day click goes to it (it opens the clock and decides which bound the day is), and dragging a range is off, so
 * the days only ever come from clicks. Otherwise it is the stock behaviour.
 */
@Injectable()
export class AuditRangeSelectionStrategy extends DefaultMatCalendarRangeStrategy<Date> {
  interceptor: AuditDayClickInterceptor | null = null;

  constructor(dateAdapter: DateAdapter<Date>) {
    super(dateAdapter);
  }

  override selectionFinished(date: Date | null, currentRange: DateRange<Date>, event?: Event): DateRange<Date> {
    return this.interceptor?.active()
      ? this.interceptor.dayClick(date, event)
      : super.selectionFinished(date as Date, currentRange);
  }

  override createDrag(dragOrigin: Date, originalRange: DateRange<Date>, newDate: Date): DateRange<Date> | null {
    return this.interceptor?.active() ? null : super.createDrag(dragOrigin, originalRange, newDate);
  }
}
