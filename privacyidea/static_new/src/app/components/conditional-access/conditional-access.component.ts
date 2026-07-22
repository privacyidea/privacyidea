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
import { Component, computed, ElementRef, inject, signal, ViewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatIconModule } from "@angular/material/icon";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  LockoutPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import {
  ConditionalAccessToggleAction,
  ConditionalAccessToggleDialogComponent
} from "./conditional-access-toggle-dialog/conditional-access-toggle-dialog.component";

@Component({
  selector: "app-conditional-access",
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginator,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatSlideToggleModule,
    MatTooltipModule,
    ScrollToTopDirective,
    MatFormField,
    MatLabel,
    ClearableInputComponent,
    MatInput
  ],
  templateUrl: "./conditional-access.component.html",
  styleUrl: "./conditional-access.component.scss"
})
export class ConditionalAccessComponent {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength = computed(() => this.policyService.policies().length);

  // Rows selected via the checkbox column; the "Delete Selected" table action acts on these.
  policySelection = signal<LockoutPolicy[]>([]);

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  displayedColumns: string[] = [
    "select",
    "name",
    "priority",
    "time_window_seconds",
    "counter_types_to_track",
    "stages",
    "threshold",
    "actions",
    "enabled",
    "dry_run"
  ];

  policyDataSource = computed(() => {
    const policies = this.policyService.policies();
    const dataSource = new MatTableDataSource(policies);
    dataSource.paginator = this.paginator;
    dataSource.sort = this.sort;
    dataSource.filterPredicate = (policy: LockoutPolicy, filter: string) =>
      policy.name.toLowerCase().includes(filter) ||
      policy.counter_types_to_track.some((type) => type.toLowerCase().includes(filter));
    return dataSource;
  });

  thresholdDisplay(policy: LockoutPolicy): string {
    return policy.stages.map((stage) => stage.failure_threshold).join(", ");
  }

  actionsDisplay(policy: LockoutPolicy): string {
    return policy.stages.flatMap((stage) => stage.actions.map((action) => action.action_type)).join(", ");
  }

  isAllSelected(): boolean {
    const rows = this.policyDataSource().data;
    return rows.length > 0 && this.policySelection().length === rows.length;
  }

  toggleAllRows(): void {
    if (this.isAllSelected()) {
      this.policySelection.set([]);
    } else {
      this.policySelection.set([...this.policyDataSource().data]);
    }
  }

  toggleRow(policy: LockoutPolicy): void {
    const current = this.policySelection();
    if (current.includes(policy)) {
      this.policySelection.set(current.filter((row) => row !== policy));
    } else {
      this.policySelection.set([...current, policy]);
    }
  }

  isSelected(policy: LockoutPolicy): boolean {
    return this.policySelection().includes(policy);
  }

  async deleteSelected(): Promise<void> {
    const selected = this.policySelection();
    if (selected.length === 0) {
      return;
    }
    const deleted = await this.policyService.deleteSelectedWithConfirmDialog(
      selected.map((policy) => ({ id: policy.id, name: policy.name }))
    );
    if (deleted) {
      this.policySelection.set([]);
    }
  }

  // Resolve the target boolean for a row from the chosen dialog action: "activate"
  // forces on, "deactivate" forces off, "toggle" flips the row's current state.
  private resolveToggle(action: ConditionalAccessToggleAction, current: boolean): boolean {
    return action === "activate" ? true : action === "deactivate" ? false : !current;
  }

  toggleEnabledSelected(): void {
    const selected = this.policySelection();
    if (selected.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: ConditionalAccessToggleDialogComponent,
        data: {
          title: $localize`(De)activate Selected Policies`,
          intro: $localize`The following policies will be toggled:`,
          onWord: $localize`enabled`,
          offWord: $localize`disabled`,
          items: selected.map((policy) => ({ label: policy.name, state: policy.enabled }))
        }
      })
      .afterClosed()
      .subscribe((action: ConditionalAccessToggleAction | undefined) => {
        if (!action) {
          return;
        }
        selected.forEach((policy) => {
          if (this.resolveToggle(action, policy.enabled)) {
            this.policyService.enablePolicy(policy.id);
          } else {
            this.policyService.disablePolicy(policy.id);
          }
        });
        this.policySelection.set([]);
      });
  }

  toggleDryRunSelected(): void {
    const selected = this.policySelection();
    if (selected.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: ConditionalAccessToggleDialogComponent,
        data: {
          title: $localize`Toggle Dry Run For Selected Policies`,
          intro: $localize`The dry-run mode of the following policies will be toggled:`,
          onWord: $localize`dry-run`,
          offWord: $localize`enforce`,
          items: selected.map((policy) => ({ label: policy.name, state: policy.dry_run }))
        }
      })
      .afterClosed()
      .subscribe((action: ConditionalAccessToggleAction | undefined) => {
        if (!action) {
          return;
        }
        selected.forEach((policy) =>
          this.policyService.savePolicy({ ...policy, dry_run: this.resolveToggle(action, policy.dry_run) })
        );
        this.policySelection.set([]);
      });
  }

  onCreatePolicy(): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_NEW);
  }

  onEditPolicy(policy: LockoutPolicy): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS + policy.id);
  }

  onToggleEnabled(policy: LockoutPolicy): void {
    if (policy.enabled) {
      this.policyService.disablePolicy(policy.id);
    } else {
      this.policyService.enablePolicy(policy.id);
    }
  }

  onToggleDryRun(policy: LockoutPolicy): void {
    this.policyService.savePolicy({ ...policy, dry_run: !policy.dry_run });
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);
    const ds = this.policyDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.policyDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
