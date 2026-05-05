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
import { Component, inject, linkedSignal, WritableSignal } from "@angular/core";
import { MatDivider } from "@angular/material/divider";
import { MatAccordion } from "@angular/material/expansion";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService } from "@services/auth/auth.service";
import { EMPTY_PERIODIC_TASK, PeriodicTask, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { PeriodicTaskPanelNewComponent } from "./periodic-task-panel/periodic-task-panel-new.component";
import { PeriodicTaskPanelComponent } from "./periodic-task-panel/periodic-task-panel.component";

@Component({
  selector: "app-periodic-task",
  standalone: true,
  templateUrl: "./periodic-task.component.html",
  imports: [ScrollToTopDirective, MatAccordion, PeriodicTaskPanelComponent, PeriodicTaskPanelNewComponent, MatDivider],
  styleUrls: ["./periodic-task.component.scss"]
})
export class PeriodicTaskComponent {
  protected readonly periodicTaskService = inject(PeriodicTaskService);
  protected readonly authService = inject(AuthService);

  periodicTasks: WritableSignal<PeriodicTask[] | undefined> = linkedSignal({
    source: () =>
      this.periodicTaskService.periodicTasksResource.hasValue()
        ? this.periodicTaskService.periodicTasksResource.value()
        : undefined,
    computation: (periodicTasksResource) => {
      if (!periodicTasksResource) return [];
      return periodicTasksResource.result?.value ?? [];
    }
  });

  newTask: PeriodicTask = { ...EMPTY_PERIODIC_TASK };

  ngOnInit() {
    this.periodicTaskService.fetchAllModuleOptions();
  }

  resetNewTask() {
    this.newTask = { ...EMPTY_PERIODIC_TASK };
  }
}
