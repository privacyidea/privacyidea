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
import { LiveAnnouncer } from "@angular/cdk/a11y";
import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  signal,
  untracked,
  ViewChild
} from "@angular/core";
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
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
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
    MatInput,
    InfoHintComponent
  ],
  templateUrl: "./conditional-access.component.html",
  styleUrl: "./conditional-access.component.scss"
})
export class ConditionalAccessComponent implements OnDestroy {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  // Announces staged reorder moves to screen readers
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  private readonly pendingChangesService = inject(PendingChangesService);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength = computed(() => this.policyService.policies().length);

  // Rows selected via the checkbox column; the "Delete Selected" table action acts on these.
  policySelection = signal<ConditionalAccessPolicy[]>([]);

  priorityReorderHint = $localize`Move policies with the arrows in the Priority column to change the order they are evaluated in. Priorities are only relevant for the actions DENY and ALLOW.`;
  priorityReorderHintAriaLabel = $localize`About rearranging priorities`;

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
    dataSource.filterPredicate = (policy: ConditionalAccessPolicy, filter: string) =>
      policy.name.toLowerCase().includes(filter) ||
      policy.counter_types_to_track.some((type) => type.toLowerCase().includes(filter));
    return dataSource;
  });

  // Reordering is an explicit, opt-in mode rather than always-on controls: it is a rare
  // operation and the arrows would otherwise clutter every row. While the mode is on the
  // table shows the draft order (not the sorted/filtered/paginated view, in which "the row
  // above" would not be the next-higher-precedence policy), moves are staged locally and
  // nothing is written until Save. Cancel simply drops the draft.
  reorderMode = signal(false);
  private readonly draftOrder = signal<ConditionalAccessPolicy[]>([]);
  // The order as it stood when the mode was entered; see startReorder/movedRows.
  private readonly baselineOrder = signal<ConditionalAccessPolicy[]>([]);
  reorderSaving = signal(false);
  // Set when a save is rejected: the draft is stale and must be replaced by the reloaded
  // order as soon as it arrives (see the effect in the constructor).
  private readonly reseedPending = signal(false);

  // The evaluation order as persisted, derived from priority rather than from the table,
  // so the draft always starts from the real order.
  private readonly orderedPolicies = computed(() =>
    [...this.policyService.policies()].sort((a, b) => a.priority - b.priority)
  );

  // While reordering, the table renders the draft array directly so the rows are the draft
  // order; otherwise it renders the normal sorted/filtered/paginated data source.
  reorderDraft = computed(() => this.draftOrder());
  // Compared against the entry snapshot rather than the live list, so this answers "did
  // the admin move something", not "does the draft still match the server". A policy
  // created or deleted in another session therefore does not light up Save or trigger the
  // discard prompt; a genuinely conflicting order is caught by the save's assertion.
  hasOrderChanges = computed(() => {
    const baseline = this.baselineOrder();
    const draft = this.draftOrder();
    return draft.length !== baseline.length || draft.some((policy, index) => policy.id !== baseline[index].id);
  });

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.reorderMode() && this.hasOrderChanges());
    this.pendingChangesService.registerValidChanges(() => this.hasOrderChanges());
    this.pendingChangesService.registerSave(() => this.saveReorder());

    // A rejected save leaves the mode open on a draft built from an order the server no
    // longer has, so the reload it triggered has to be adopted before the admin can do
    // anything meaningful. Only the arrival of fresh data is a trigger (the flag is read
    // untracked): re-seeding the instant the flag is set would just re-read the stale list
    // and clear it before the response lands.
    effect(() => {
      this.policyService.policies();
      untracked(() => {
        if (!this.reseedPending() || !this.reorderMode()) {
          return;
        }
        const order = this.orderedPolicies();
        this.baselineOrder.set(order);
        this.draftOrder.set(order);
        this.reseedPending.set(false);
      });
    });
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  startReorder(): void {
    const order = this.orderedPolicies();
    this.draftOrder.set(order);
    // Frozen at entry: the draft is diffed against this to find the rows that moved, and
    // it is what the save asserts the server still holds (see movedRows).
    this.baselineOrder.set(order);
    this.policySelection.set([]);
    this.reorderMode.set(true);
  }

  // The rows whose position changed, in their new relative order, plus the priority each
  // held when the mode was entered. Sending only these is equivalent to sending the whole
  // list - the moved rows are the permutation's support, so the values they collectively
  // hold are unchanged - and it keeps the conflict check scoped to rows this admin
  // actually touched, so two admins reordering different parts of the list both succeed.
  private movedRows(): { ids: number[]; expectedPriorities: number[] } {
    const baseline = this.baselineOrder();
    const moved = this.draftOrder().filter((policy, index) => policy.id !== baseline[index]?.id);
    return {
      ids: moved.map((policy) => policy.id),
      expectedPriorities: moved.map((policy) => policy.priority)
    };
  }

  // Leaving rearrange mode with staged moves would silently throw them away, so confirm
  // first - but only when the draft actually differs from the persisted order, so simply
  // opening and closing the mode never asks.
  async cancelReorder(): Promise<void> {
    if (this.hasOrderChanges()) {
      const discard = await this.dialogService.confirm({
        title: $localize`Discard the new order?`,
        message: $localize`The rearranged evaluation order has not been saved. Discard the changes?`,
        confirmButtonText: $localize`Discard`
      });
      if (!discard) {
        return;
      }
    }
    this.exitReorderMode();
  }

  private exitReorderMode(): void {
    this.reorderMode.set(false);
    this.draftOrder.set([]);
    this.baselineOrder.set([]);
  }

  // One request for the whole rearrangement: the draft ids in their new order take the
  // priority values this same set already holds, so nothing is renumbered and any
  // numbering scheme (1,2,3 as much as 10,20,30) reorders identically.
  // Returns whether the order is persisted, so the pending-changes guard can offer
  // "Save & Exit" and only let the navigation through once the write succeeded.
  async saveReorder(): Promise<boolean> {
    if (!this.hasOrderChanges()) {
      this.exitReorderMode();
      return true;
    }
    this.reorderSaving.set(true);
    try {
      const { ids, expectedPriorities } = this.movedRows();
      const saved = await this.policyService.reorderPolicies(ids, expectedPriorities);
      if (saved) {
        this.exitReorderMode();
      } else {
        // Stay in the mode - the admin still wants to reorder - but the draft is now built
        // on an order the server rejected, so hand it over to the reload the service just
        // triggered. Keeping the draft rows and only refreshing their numbers is not an
        // option: the draft would still describe a move against the old order and saving it
        // again would undo whatever the other admin did.
        this.reseedPending.set(true);
      }
      return saved;
    } finally {
      this.reorderSaving.set(false);
    }
  }

  canMoveUp(policy: ConditionalAccessPolicy): boolean {
    return this.draftIndex(policy) > 0;
  }

  canMoveDown(policy: ConditionalAccessPolicy): boolean {
    const index = this.draftIndex(policy);
    return index >= 0 && index < this.draftOrder().length - 1;
  }

  moveUpLabel(policy: ConditionalAccessPolicy): string {
    return $localize`Move ${policy.name} up, so it is evaluated earlier`;
  }

  moveDownLabel(policy: ConditionalAccessPolicy): string {
    return $localize`Move ${policy.name} down, so it is evaluated later`;
  }

  moveUp(policy: ConditionalAccessPolicy): void {
    this.swapDraft(this.draftIndex(policy), -1);
  }

  moveDown(policy: ConditionalAccessPolicy): void {
    this.swapDraft(this.draftIndex(policy), 1);
  }

  // Reordering is the one action here whose entire result is *where* a row sits, and that
  // is conveyed only visually: the arrows keep their labels, the row content is unchanged,
  // and the table is re-rendered without moving focus, so nothing a screen reader tracks
  // changes when a move succeeds. Without this announcement a non-sighted admin pressing
  // "Move X up" gets no confirmation that anything happened, nor where the policy landed.
  private announceMove(policy: ConditionalAccessPolicy): void {
    const position = this.draftIndex(policy) + 1;
    const total = this.draftOrder().length;
    this.liveAnnouncer.announce($localize`${policy.name} moved to position ${position} of ${total}`);
  }

  // The priority shown per row while reordering: the draft position takes the priority
  // value that position already holds, so the admin sees the numbers the save will write.
  draftPriority(policy: ConditionalAccessPolicy): number {
    const index = this.draftIndex(policy);
    const values = this.draftOrder()
      .map((candidate) => candidate.priority)
      .sort((a, b) => a - b);
    return index >= 0 ? values[index] : policy.priority;
  }

  private swapDraft(index: number, offset: number): void {
    const draft = [...this.draftOrder()];
    const target = index + offset;
    if (index < 0 || target < 0 || target >= draft.length) {
      return;
    }
    [draft[index], draft[target]] = [draft[target], draft[index]];
    this.draftOrder.set(draft);
    // The rows are re-rendered silently, so a screen reader would otherwise get no
    // feedback that anything happened.
    this.announceMove(draft[target]);
  }

  private draftIndex(policy: ConditionalAccessPolicy): number {
    return this.draftOrder().findIndex((candidate) => candidate.id === policy.id);
  }

  thresholdDisplay(policy: ConditionalAccessPolicy): string {
    return policy.stages.map((stage) => stage.failure_threshold).join(", ");
  }

  actionsDisplay(policy: ConditionalAccessPolicy): string {
    return policy.stages.flatMap((stage) => stage.actions.map((action) => action.action_type)).join(", ");
  }

  // A policy whose conditions name values that no longer exist - typically a deleted realm - is
  // flagged here rather than given a column of its own: the table is already wide, and what the admin
  // needs from the list is only whether a policy needs attention. The condition has silently stopped
  // doing what it was written to do, and the backend will refuse to save the policy until it is fixed.
  hasStaleConditions(policy: ConditionalAccessPolicy): boolean {
    return this.policyService.staleConditionValues(policy.conditions).length > 0;
  }

  staleConditionsTooltip = $localize`This policy has conditions that are no longer valid.`;

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

  toggleRow(policy: ConditionalAccessPolicy): void {
    const current = this.policySelection();
    if (current.includes(policy)) {
      this.policySelection.set(current.filter((row) => row !== policy));
    } else {
      this.policySelection.set([...current, policy]);
    }
  }

  isSelected(policy: ConditionalAccessPolicy): boolean {
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
          this.policyService.setDryRun(policy.id, this.resolveToggle(action, policy.dry_run))
        );
        this.policySelection.set([]);
      });
  }

  // Leaving the list for the create page ends the rearrangement either way, so drop the
  // draft rather than block the action: exiting first also settles the pending-changes
  // guard, so the admin is not asked to confirm a discard they just chose.
  onCreatePolicy(): void {
    this.exitReorderMode();
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_NEW);
  }

  onEditPolicy(policy: ConditionalAccessPolicy): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS + policy.id);
  }

  onToggleEnabled(policy: ConditionalAccessPolicy): void {
    if (policy.enabled) {
      this.policyService.disablePolicy(policy.id);
    } else {
      this.policyService.enablePolicy(policy.id);
    }
  }

  onToggleDryRun(policy: ConditionalAccessPolicy): void {
    this.policyService.setDryRun(policy.id, !policy.dry_run);
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
