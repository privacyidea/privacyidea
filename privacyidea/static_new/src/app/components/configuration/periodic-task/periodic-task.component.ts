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
import { Component, computed, inject, OnInit, signal, ViewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox, MatCheckboxChange } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import {
  PERIODIC_TASK_MODULE_MAPPING,
  PeriodicTask,
  PeriodicTaskModule,
  PeriodicTaskService,
  PeriodicTaskServiceInterface
} from "@services/periodic-task/periodic-task.service";
import { firstValueFrom, lastValueFrom } from "rxjs";

@Component({
  selector: "app-periodic-task",
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatCheckbox,
    MatSlideToggle,
    MatFormField,
    MatLabel,
    MatInput,
    ClearableInputComponent,
    CopyableComponent,
    ScrollToTopDirective
  ],
  templateUrl: "./periodic-task.component.html",
  styleUrls: ["./periodic-task.component.scss"]
})
export class PeriodicTaskComponent implements OnInit {
  protected readonly periodicTaskService: PeriodicTaskServiceInterface = inject(PeriodicTaskService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly notificationService = inject(NotificationService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private readonly router = inject(Router);

  filterString = signal<string>("");

  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: any;

  displayedColumns: string[] = ["select", "name", "taskmodule", "interval", "nodes", "options", "active"];

  protected readonly Object = Object;
  detailedView = signal<boolean>(false);

  toggleDetailedView(): void {
    this.detailedView.set(!this.detailedView());
  }

  isBooleanValue(value: any): boolean {
    return ["true", "false"].includes(String(value).toLowerCase());
  }

  formatOptions(options: Record<string, any>): string {
    if (!options || typeof options !== "object") return "";
    return Object.entries(options)
      .map(([key, value]) => (this.isBooleanValue(value) ? key : `${key}: ${value}`))
      .join(", ");
  }

  periodicTasks = computed<PeriodicTask[]>(() => {
    const resource = this.periodicTaskService.periodicTasksResource;
    if (!resource.hasValue()) return [];
    return resource.value()?.result?.value ?? [];
  });

  periodicTasksDataSource = computed(() => {
    const tasks = this.periodicTasks();
    const dataSource = new MatTableDataSource(tasks);
    dataSource.sort = this.sort;
    dataSource.filterPredicate = (task, filter) => this.matchesFilter(task, filter);
    dataSource.filter = this.filterString().toLowerCase();
    return dataSource;
  });

  matchesFilter(task: PeriodicTask, filter: string): boolean {
    const haystack = [
      task.name,
      this.getModuleLabel(task.taskmodule),
      task.interval,
      (task.nodes ?? []).join(", "),
      this.formatOptions(task.options),
      task.active ? "active" : "inactive"
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(filter);
  }

  selectedTaskIds = signal<Set<number>>(new Set());

  selectableTaskIds = computed<number[]>(() =>
    this.periodicTasks()
      .map((t) => t.id)
      .filter((id): id is number => id != null)
  );

  ngOnInit(): void {
    this.periodicTaskService.fetchAllModuleOptions();
  }

  onCreateNewTask(): void {
    this.router.navigateByUrl(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS_NEW);
  }

  onEditTask(task: PeriodicTask): void {
    this.router.navigateByUrl(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS_DETAILS + task.name);
  }

  toggleActive(task: PeriodicTask, activate: boolean): void {
    if (task.id == null) return;
    if (activate) {
      this.periodicTaskService.enablePeriodicTask(task.id);
    } else {
      this.periodicTaskService.disablePeriodicTask(task.id);
    }
  }

  updateSelection(event: MatCheckboxChange, task: PeriodicTask): void {
    if (task.id == null) return;
    const selected = new Set(this.selectedTaskIds());
    if (event.checked) {
      selected.add(task.id);
    } else {
      selected.delete(task.id);
    }
    this.selectedTaskIds.set(selected);
  }

  isAllSelected(): boolean {
    const ids = this.selectableTaskIds();
    if (ids.length === 0) return false;
    const selected = this.selectedTaskIds();
    return ids.every((id) => selected.has(id));
  }

  masterToggle(): void {
    const ids = this.selectableTaskIds();
    if (this.isAllSelected()) {
      this.selectedTaskIds.set(new Set());
    } else {
      this.selectedTaskIds.set(new Set(ids));
    }
  }

  async deleteSelected(): Promise<void> {
    const selectedIds = this.selectedTaskIds();
    if (selectedIds.size === 0) return;
    const selectedTasks = this.periodicTasks().filter((t) => t.id != null && selectedIds.has(t.id));
    const confirmed = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`Delete Periodic Tasks`,
            items: selectedTasks.map((t) => t.name),
            itemType: $localize`Periodic Tasks`,
            confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
          }
        })
        .afterClosed()
    );
    if (!confirmed) return;
    for (const task of selectedTasks) {
      if (task.id == null) continue;
      try {
        await firstValueFrom(this.periodicTaskService.deletePeriodicTask(task.id));
        this.notificationService.success("Successfully deleted periodic task.");
      } catch {
        // error notification already surfaced by deletePeriodicTask
      }
    }
    this.selectedTaskIds.set(new Set());
    this.periodicTaskService.periodicTasksResource.reload();
  }

  getModuleLabel(module: string): string {
    return PERIODIC_TASK_MODULE_MAPPING[module as PeriodicTaskModule] ?? module;
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);
    const dataSource = this.periodicTasksDataSource();
    dataSource.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const dataSource = this.periodicTasksDataSource();
    dataSource.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}