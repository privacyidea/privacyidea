/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, input } from "@angular/core";
import { EMPTY_PERIODIC_TASK, PeriodicTask } from "../../../../../services/periodic-task/periodic-task.service";
import { DatePipe } from "@angular/common";
import { MatIcon } from "@angular/material/icon";
import { parseBooleanValue } from "../../../../../utils/parse-boolean-value";

@Component({
  selector: "app-periodic-task-read",
  templateUrl: "./periodic-task-read.component.html",
  styleUrl: "./periodic-task-read.component.scss",
  imports: [
    DatePipe,
    MatIcon
  ]
})
export class PeriodicTaskReadComponent {
  task = input<PeriodicTask>(EMPTY_PERIODIC_TASK);

  isDateValue(val: unknown): val is string | number | Date {
    return typeof val === "string" || typeof val === "number" || val instanceof Date;
  }

  lastRunsEntries(obj: unknown): { key: string, value: any }[] {
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      return Object.entries(obj as Record<string, any>).map(([key, value]) => ({ key, value }));
    }
    return [];
  }

  protected readonly Array = Array;
  protected readonly Object = Object;

  isBooleanAction(param: any) {
    return ["true", "false"].includes(param.toLowerCase());
  }

  protected readonly parseBooleanValue = parseBooleanValue;
}