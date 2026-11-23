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
import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDatepickerModule, MatDateRangePicker } from "@angular/material/datepicker";
import { MatIconModule } from "@angular/material/icon";
import { AuditService, AuditServiceInterface } from "@services/audit/audit.service";

/**
 * Calendar header of the audit date range picker: the stock header plus a row with a button at the left that drops the
 * active range and closes the picker, and the "Time" checkbox at the right. Unchecked, selecting dates applies whole
 * days instantly. Checked, each clicked day opens a clock to pick its time (see AuditComponent.onTimedDayClick).
 */
@Component({
  selector: "app-audit-date-range-header",
  imports: [MatDatepickerModule, MatButtonModule, MatCheckbox, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./audit-date-range-header.component.html",
  styleUrl: "./audit-date-range-header.component.scss"
})
export class AuditDateRangeHeaderComponent {
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  private readonly picker = inject<MatDateRangePicker<Date>>(MatDateRangePicker, { optional: true });

  readonly hasRange = computed(() => !!this.auditService.timestampFrom() || !!this.auditService.timestampTo());

  readonly timeMode = this.auditService.rangeTimeMode;

  onTimeModeChange(checked: boolean): void {
    this.auditService.rangeTimeMode.set(checked);
  }

  clear(): void {
    this.auditService.timestampFrom.set(null);
    this.auditService.timestampTo.set(null);
    this.auditService.updateFilter((current) => current.removeKey("startdate"));
    this.picker?.close();
  }
}
