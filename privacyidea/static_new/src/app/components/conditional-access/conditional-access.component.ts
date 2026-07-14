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
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatIconModule } from "@angular/material/icon";
import { MatPaginator } from "@angular/material/paginator";
import { MatSelectModule } from "@angular/material/select";
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
  ALL_AUTH_EVENT_TYPES,
  AuthEventType,
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  LockoutPolicy,
  LockoutPolicySaveParams
} from "@services/conditional-access/conditional-access-policy.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { deepCopy } from "@utils/deep-copy.utils";

@Component({
  selector: "app-conditional-access",
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginator,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
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
  protected readonly allAuthEventTypes = ALL_AUTH_EVENT_TYPES;
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength = computed(() => this.policyService.policies().length);

  // Inline row edit: the id of the row currently in edit mode and a working copy of that policy.
  // Editing writes through the buffer; saveEdit() persists it, cancelEdit() drops it.
  editingPolicyId = signal<number | null>(null);
  editBuffer = signal<LockoutPolicySaveParams | null>(null);

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  displayedColumns: string[] = [
    "name",
    "priority",
    "time_window_seconds",
    "counter_types_to_track",
    "stages",
    "threshold",
    "enabled",
    "dry_run",
    "actions"
  ];

  // A threshold is a per-stage value; a single-stage policy can be edited inline, while a
  // multi-stage policy shows its thresholds joined and is edited on the full edit page.
  editIsSingleStage = computed(() => (this.editBuffer()?.stages.length ?? 0) === 1);
  editThreshold = computed(() => this.editBuffer()?.stages[0]?.failure_threshold ?? null);

  canSaveEdit = computed(() => {
    const buffer = this.editBuffer();
    if (!buffer) {
      return false;
    }
    const name = buffer.name.trim();
    const nameValid = name.length > 0 && name.length <= 255;
    const priorityValid = Number.isInteger(buffer.priority) && buffer.priority >= 1;
    const timeWindowValid = Number.isInteger(buffer.time_window_seconds) && buffer.time_window_seconds >= 1;
    const counterTypesValid = buffer.counter_types_to_track.length > 0;
    const thresholdValid = buffer.stages.length !== 1 || buffer.stages[0].failure_threshold >= 1;
    return nameValid && priorityValid && timeWindowValid && counterTypesValid && thresholdValid;
  });

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

  isEditing(policy: LockoutPolicy): boolean {
    return this.editingPolicyId() === policy.id;
  }

  startEdit(policy: LockoutPolicy): void {
    this.editBuffer.set(deepCopy(policy) as LockoutPolicySaveParams);
    this.editingPolicyId.set(policy.id);
  }

  cancelEdit(): void {
    this.editingPolicyId.set(null);
    this.editBuffer.set(null);
  }

  async saveEdit(): Promise<void> {
    const buffer = this.editBuffer();
    if (!buffer || !this.canSaveEdit()) {
      return;
    }
    const savedId = await this.policyService.savePolicy(buffer);
    if (savedId !== undefined) {
      this.cancelEdit();
    }
  }

  private updateBuffer(partial: Partial<LockoutPolicySaveParams>): void {
    const buffer = this.editBuffer();
    if (buffer) {
      this.editBuffer.set({ ...buffer, ...partial });
    }
  }

  setEditName(value: string): void {
    this.updateBuffer({ name: value });
  }

  setEditPriority(value: string): void {
    this.updateBuffer({ priority: parseInt(value, 10) });
  }

  setEditTimeWindow(value: string): void {
    this.updateBuffer({ time_window_seconds: parseInt(value, 10) });
  }

  setEditCounterTypes(value: AuthEventType[]): void {
    this.updateBuffer({ counter_types_to_track: value });
  }

  setEditThreshold(value: string): void {
    const buffer = this.editBuffer();
    if (!buffer || buffer.stages.length !== 1) {
      return;
    }
    const stages = buffer.stages.map((stage, index) =>
      index === 0 ? { ...stage, failure_threshold: parseInt(value, 10) } : stage
    );
    this.updateBuffer({ stages });
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

  async onDeletePolicy(policy: LockoutPolicy): Promise<void> {
    await this.policyService.deleteWithConfirmDialog(policy);
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
