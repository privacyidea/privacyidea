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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { LiveAnnouncer } from "@angular/cdk/a11y";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  LockoutPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockAuthService,
  MockConditionalAccessPolicyService,
  MockDialogService,
  MockPendingChangesService,
  MockTableUtilsService
} from "@testing/mock-services";
import { Subject } from "rxjs";
import { ConditionalAccessToggleAction } from "./conditional-access-toggle-dialog/conditional-access-toggle-dialog.component";
import { ConditionalAccessComponent } from "./conditional-access.component";

describe("ConditionalAccessComponent", () => {
  let component: ConditionalAccessComponent;
  let fixture: ComponentFixture<ConditionalAccessComponent>;
  let policyServiceMock: MockConditionalAccessPolicyService;
  let dialogServiceMock: MockDialogService;
  let pendingChangesServiceMock: MockPendingChangesService;
  let dialogClosed: Subject<ConditionalAccessToggleAction | undefined>;
  let router: Router;

  const samplePolicy: LockoutPolicy = {
    id: 1,
    name: "Brute Force",
    time_window_seconds: 600,
    enabled: true,
    dry_run: false,
    priority: 1,
    target: "user",
    count_mode: "PER_REQUEST",
    counter_types_to_track: ["PIN_FAIL"],
    stages: [{ failure_threshold: 5, actions: [] }],
    conditions: []
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    policyServiceMock.policies.set([samplePolicy]);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesServiceMock = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(dialogClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);

    fixture = TestBed.createComponent(ConditionalAccessComponent);
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display policies from the service", () => {
    expect(component.policyDataSource().data.length).toBe(1);
    expect(component.policyDataSource().data[0].name).toBe("Brute Force");
  });

  it("should filter by name and by tracked event type", () => {
    component.onFilterInput("brute");
    expect(component.policyDataSource().filter).toBe("brute");
    component.resetFilter();
    expect(component.filterString()).toBe("");
    expect(component.policyDataSource().filter).toBe("");
  });

  it("should navigate to the create page", () => {
    component.onCreatePolicy();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_NEW);
  });

  it("should navigate to the edit page for a policy", () => {
    component.onEditPolicy(samplePolicy);
    expect(router.navigateByUrl).toHaveBeenCalledWith(
      ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS + samplePolicy.id
    );
  });

  it("should disable an enabled policy on toggle", () => {
    component.onToggleEnabled(samplePolicy);
    expect(policyServiceMock.disablePolicy).toHaveBeenCalledWith(1);
  });

  it("should enable a disabled policy on toggle", () => {
    component.onToggleEnabled({ ...samplePolicy, enabled: false });
    expect(policyServiceMock.enablePolicy).toHaveBeenCalledWith(1);
  });

  it("should join all stage thresholds for display", () => {
    const multiStage: LockoutPolicy = {
      ...samplePolicy,
      stages: [
        { failure_threshold: 3, actions: [] },
        { failure_threshold: 5, actions: [] }
      ]
    };
    expect(component.thresholdDisplay(multiStage)).toBe("3, 5");
  });

  it("should list every action type across all stages", () => {
    const policy: LockoutPolicy = {
      ...samplePolicy,
      stages: [
        { failure_threshold: 3, actions: [{ action_type: "LOCK_USER", action_value: 60 }] },
        {
          failure_threshold: 5,
          actions: [
            { action_type: "EMAIL_ADMIN", action_value: null },
            { action_type: "BLOCK_IP", action_value: 60 }
          ]
        }
      ]
    };
    expect(component.actionsDisplay(policy)).toBe("LOCK_USER, EMAIL_ADMIN, BLOCK_IP");
  });

  describe("selection", () => {
    const otherPolicy: LockoutPolicy = { ...samplePolicy, id: 2, name: "Second" };

    beforeEach(() => {
      policyServiceMock.policies.set([samplePolicy, otherPolicy]);
    });

    it("should toggle a single row on and off", () => {
      component.toggleRow(samplePolicy);
      expect(component.isSelected(samplePolicy)).toBe(true);
      component.toggleRow(samplePolicy);
      expect(component.isSelected(samplePolicy)).toBe(false);
    });

    it("should select and clear all rows", () => {
      expect(component.isAllSelected()).toBe(false);
      component.toggleAllRows();
      expect(component.isAllSelected()).toBe(true);
      expect(component.policySelection().length).toBe(2);
      component.toggleAllRows();
      expect(component.policySelection().length).toBe(0);
    });

    it("should not report all-selected when there are no rows", () => {
      policyServiceMock.policies.set([]);
      expect(component.isAllSelected()).toBe(false);
    });
  });

  describe("delete selected", () => {
    const otherPolicy: LockoutPolicy = { ...samplePolicy, id: 2, name: "Second" };

    it("should do nothing when nothing is selected", async () => {
      await component.deleteSelected();
      expect(policyServiceMock.deleteSelectedWithConfirmDialog).not.toHaveBeenCalled();
    });

    it("should delete the selected rows and clear the selection", async () => {
      component.policySelection.set([samplePolicy, otherPolicy]);
      await component.deleteSelected();
      expect(policyServiceMock.deleteSelectedWithConfirmDialog).toHaveBeenCalledWith([
        { id: 1, name: "Brute Force" },
        { id: 2, name: "Second" }
      ]);
      expect(component.policySelection().length).toBe(0);
    });

    it("should keep the selection when the delete is cancelled", async () => {
      policyServiceMock.deleteSelectedWithConfirmDialog.mockResolvedValueOnce(false);
      component.policySelection.set([samplePolicy]);
      await component.deleteSelected();
      expect(component.policySelection().length).toBe(1);
    });
  });

  describe("bulk (de)activate / dry run", () => {
    const enabledPolicy: LockoutPolicy = { ...samplePolicy, id: 1, enabled: true };
    const disabledPolicy: LockoutPolicy = { ...samplePolicy, id: 2, name: "Second", enabled: false };

    function emitAction(action: ConditionalAccessToggleAction | undefined): void {
      dialogClosed.next(action);
      dialogClosed.complete();
    }

    it("should open the (de)activate dialog and flip each policy on 'toggle'", () => {
      component.policySelection.set([enabledPolicy, disabledPolicy]);
      component.toggleEnabledSelected();
      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
      emitAction("toggle");
      expect(policyServiceMock.disablePolicy).toHaveBeenCalledWith(1);
      expect(policyServiceMock.enablePolicy).toHaveBeenCalledWith(2);
      expect(component.policySelection().length).toBe(0);
    });

    it("should force-enable every policy on 'activate'", () => {
      component.policySelection.set([enabledPolicy, disabledPolicy]);
      component.toggleEnabledSelected();
      emitAction("activate");
      expect(policyServiceMock.enablePolicy).toHaveBeenCalledWith(1);
      expect(policyServiceMock.enablePolicy).toHaveBeenCalledWith(2);
      expect(policyServiceMock.disablePolicy).not.toHaveBeenCalled();
    });

    it("should force-deactivate every policy on 'deactivate'", () => {
      component.policySelection.set([enabledPolicy, disabledPolicy]);
      component.toggleEnabledSelected();
      emitAction("deactivate");
      expect(policyServiceMock.disablePolicy).toHaveBeenCalledWith(1);
      expect(policyServiceMock.disablePolicy).toHaveBeenCalledWith(2);
      expect(policyServiceMock.enablePolicy).not.toHaveBeenCalled();
    });

    it("should do nothing when the dialog is dismissed", () => {
      component.policySelection.set([enabledPolicy]);
      component.toggleEnabledSelected();
      emitAction(undefined);
      expect(policyServiceMock.enablePolicy).not.toHaveBeenCalled();
      expect(policyServiceMock.disablePolicy).not.toHaveBeenCalled();
      expect(component.policySelection().length).toBe(1);
    });

    it("should flip dry_run through the dialog on 'toggle'", () => {
      const dryRunOff: LockoutPolicy = { ...samplePolicy, id: 1, dry_run: false };
      const dryRunOn: LockoutPolicy = { ...samplePolicy, id: 2, name: "Second", dry_run: true };
      component.policySelection.set([dryRunOff, dryRunOn]);
      component.toggleDryRunSelected();
      emitAction("toggle");
      expect(policyServiceMock.savePolicy).toHaveBeenCalledWith(expect.objectContaining({ id: 1, dry_run: true }));
      expect(policyServiceMock.savePolicy).toHaveBeenCalledWith(expect.objectContaining({ id: 2, dry_run: false }));
      expect(component.policySelection().length).toBe(0);
    });

    it("should not open a dialog when nothing is selected", () => {
      component.toggleEnabledSelected();
      component.toggleDryRunSelected();
      expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    });
  });

  describe("reordering", () => {
    const policyAt = (id: number, priority: number, name: string): LockoutPolicy => ({
      ...samplePolicy,
      id,
      name,
      priority
    });

    const first = policyAt(1, 10, "First");
    const second = policyAt(2, 20, "Second");
    const third = policyAt(3, 30, "Third");

    const reorderButtons = (): HTMLButtonElement[] =>
      Array.from(fixture.nativeElement.querySelectorAll("button.reorder-button"));

    const rowNames = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll("tbody tr td:nth-child(2)")).map((cell) =>
        (cell as HTMLElement).textContent!.trim()
      );

    beforeEach(() => {
      // Deliberately unsorted input: the draft must start from priority order.
      policyServiceMock.policies.set([third, first, second]);
      fixture.detectChanges();
    });

    it("should not show the reorder controls until the mode is entered", () => {
      expect(component.reorderMode()).toBe(false);
      expect(reorderButtons()).toEqual([]);
    });

    it("should seed the draft from priority order when entering the mode", () => {
      component.startReorder();
      fixture.detectChanges();
      expect(component.reorderMode()).toBe(true);
      expect(rowNames()).toEqual(["First", "Second", "Third"]);
      expect(reorderButtons().length).toBe(6);
    });

    it("should clear the row selection when entering the mode", () => {
      component.toggleRow(third);
      expect(component.policySelection().length).toBe(1);
      component.startReorder();
      expect(component.policySelection()).toEqual([]);
    });

    it("should stage moves locally without calling the backend", () => {
      component.startReorder();
      component.moveUp(second);
      fixture.detectChanges();
      expect(rowNames()).toEqual(["Second", "First", "Third"]);
      expect(policyServiceMock.reorderPolicies).not.toHaveBeenCalled();
    });

    it("should move down as well", () => {
      component.startReorder();
      component.moveDown(first);
      fixture.detectChanges();
      expect(rowNames()).toEqual(["Second", "First", "Third"]);
      expect(policyServiceMock.reorderPolicies).not.toHaveBeenCalled();
    });

    it("should show the priority each row would get, so Save holds no surprise", () => {
      component.startReorder();
      component.moveUp(third);
      // Third takes the value its new position already holds (20), Second drops to 30.
      expect(component.draftPriority(third)).toBe(20);
      expect(component.draftPriority(second)).toBe(30);
      expect(component.draftPriority(first)).toBe(10);
    });

    it("should not move the first row up or the last row down", () => {
      component.startReorder();
      expect(component.canMoveUp(first)).toBe(false);
      expect(component.canMoveDown(third)).toBe(false);
      component.moveUp(first);
      component.moveDown(third);
      fixture.detectChanges();
      expect(rowNames()).toEqual(["First", "Second", "Third"]);
    });

    it("should mark the boundary arrows aria-disabled but keep them focusable", () => {
      component.startReorder();
      fixture.detectChanges();
      const buttons = reorderButtons();
      expect(buttons[0].getAttribute("aria-disabled")).toBe("true"); // First: up
      expect(buttons[1].getAttribute("aria-disabled")).toBeNull(); // First: down
      expect(buttons[4].getAttribute("aria-disabled")).toBeNull(); // Third: up
      expect(buttons[5].getAttribute("aria-disabled")).toBe("true"); // Third: down
      // Not the `disabled` property: disabling the button the user just activated would drop keyboard focus to <body>
      // the moment a row reaches an end.
      buttons.forEach((button) => expect(button.disabled).toBe(false));
    });

    it("should label the arrows with the policy name for screen readers", () => {
      component.startReorder();
      fixture.detectChanges();
      const labels = reorderButtons().map((button) => button.getAttribute("aria-label"));
      expect(labels[0]).toContain("First");
      expect(labels[0]).toContain("up");
      expect(labels[1]).toContain("First");
      expect(labels[1]).toContain("down");
    });

    it("should announce the new position for screen readers", () => {
      const announce = jest.spyOn(TestBed.inject(LiveAnnouncer), "announce");
      component.startReorder();
      component.moveUp(third);
      expect(announce).toHaveBeenCalledWith("Third moved to position 2 of 3");
    });

    it("should not navigate away from a staged draft via the policy name", () => {
      component.startReorder();
      fixture.detectChanges();
      // The name is plain text while reordering, so there is no link to lose the draft to.
      expect(fixture.nativeElement.querySelectorAll("tbody a").length).toBe(0);
      component.cancelReorder();
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll("tbody a").length).toBe(3);
    });

    it("should disable the row toggles so the draft cannot go stale", () => {
      component.startReorder();
      fixture.detectChanges();
      const toggles: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll("mat-slide-toggle button"));
      expect(toggles.length).toBeGreaterThan(0);
      toggles.forEach((toggle) => expect(toggle.getAttribute("disabled")).not.toBeNull());
    });

    it("should report pending changes to the navigation guard only while a draft differs", () => {
      // The route carries pendingChangesGuard (admin.routes.ts), which reads these hooks; without them a menu click
      // would silently drop the staged order.
      const hasChanges = pendingChangesServiceMock.registerHasChanges.mock.calls[0][0] as () => boolean;
      expect(hasChanges()).toBe(false); // not in the mode at all
      component.startReorder();
      expect(hasChanges()).toBe(false); // in the mode, nothing moved
      component.moveUp(third);
      expect(hasChanges()).toBe(true);
      component.moveDown(third);
      expect(hasChanges()).toBe(false); // moved back
    });

    it("should let the guard persist the order via Save & Exit", async () => {
      const save = pendingChangesServiceMock.registerSave.mock.calls[0][0] as () => Promise<boolean>;
      component.startReorder();
      component.moveUp(third);
      await expect(save()).resolves.toBe(true);
      expect(policyServiceMock.reorderPolicies).toHaveBeenCalledWith([3, 2], [30, 20]);
    });

    it("should refuse the guard's Save & Exit when the write fails", async () => {
      policyServiceMock.reorderPolicies.mockResolvedValueOnce(false);
      const save = pendingChangesServiceMock.registerSave.mock.calls[0][0] as () => Promise<boolean>;
      component.startReorder();
      component.moveUp(third);
      await expect(save()).resolves.toBe(false);
      // Navigation stays blocked (save() resolved false) and the admin is left in the mode.
      expect(component.reorderMode()).toBe(true);
    });

    it("should keep Save disabled until something actually moved", () => {
      component.startReorder();
      expect(component.hasOrderChanges()).toBe(false);
      component.moveUp(second);
      expect(component.hasOrderChanges()).toBe(true);
      // moving it back is not a change
      component.moveDown(second);
      expect(component.hasOrderChanges()).toBe(false);
    });

    it("should send the rearrangement once on save and leave the mode", async () => {
      component.startReorder();
      component.moveUp(third);
      component.moveUp(third);
      await component.saveReorder();
      expect(policyServiceMock.reorderPolicies).toHaveBeenCalledTimes(1);
      // Every row moved here, each asserted with the priority it held at entry.
      expect(policyServiceMock.reorderPolicies).toHaveBeenCalledWith([3, 1, 2], [30, 10, 20]);
      expect(component.reorderMode()).toBe(false);
    });

    it("should send only the rows that moved, not the untouched ones", async () => {
      component.startReorder();
      component.moveUp(third); // First stays put; Third and Second swap
      await component.saveReorder();
      // "First" is absent: leaving it out keeps the conflict check scoped to the rows this admin actually touched, so a
      // concurrent edit elsewhere in the list does not clash.
      expect(policyServiceMock.reorderPolicies).toHaveBeenCalledWith([3, 2], [30, 20]);
    });

    it("should not call the backend when saving an unchanged order", async () => {
      component.startReorder();
      await component.saveReorder();
      expect(policyServiceMock.reorderPolicies).not.toHaveBeenCalled();
      expect(component.reorderMode()).toBe(false);
    });

    it("should stay in the mode on a failed save and adopt the reloaded order", async () => {
      // The draft was built on an order the server rejected, so it is replaced by the refreshed list as soon as it
      // arrives, leaving the admin in the mode to redo the move against the real order.
      policyServiceMock.reorderPolicies.mockResolvedValueOnce(false);
      component.startReorder();
      component.moveUp(second);
      await component.saveReorder();
      expect(component.reorderMode()).toBe(true);

      // the reload lands with the order another admin left behind
      policyServiceMock.policies.set([policyAt(1, 10, "First"), policyAt(3, 20, "Third"), policyAt(2, 30, "Second")]);
      fixture.detectChanges();

      expect(rowNames()).toEqual(["First", "Third", "Second"]);
      // Adopted as the new starting point, so Save is disabled until something moves again.
      expect(component.hasOrderChanges()).toBe(false);
      expect(reorderButtons().length).toBe(6);
    });

    it("should not adopt further reloads once the draft has been re-seeded", async () => {
      policyServiceMock.reorderPolicies.mockResolvedValueOnce(false);
      component.startReorder();
      component.moveUp(second);
      await component.saveReorder();
      policyServiceMock.policies.set([policyAt(1, 10, "First"), policyAt(3, 20, "Third"), policyAt(2, 30, "Second")]);
      fixture.detectChanges();

      // Now the admin stages a move again; an unrelated refresh must not wipe it.
      component.moveUp(second);
      expect(component.hasOrderChanges()).toBe(true);
      policyServiceMock.policies.set([policyAt(1, 10, "First"), policyAt(3, 20, "Third"), policyAt(2, 30, "Second")]);
      fixture.detectChanges();
      expect(component.hasOrderChanges()).toBe(true);
    });

    it("should confirm before discarding staged moves, then drop them", async () => {
      dialogServiceMock.confirm.mockResolvedValueOnce(true);
      component.startReorder();
      component.moveUp(third);
      await component.cancelReorder();
      fixture.detectChanges();
      expect(dialogServiceMock.confirm).toHaveBeenCalled();
      expect(component.reorderMode()).toBe(false);
      expect(policyServiceMock.reorderPolicies).not.toHaveBeenCalled();
      // the table is back to the persisted order
      expect(rowNames()).toEqual(["First", "Second", "Third"]);
      expect(reorderButtons()).toEqual([]);
    });

    it("should keep the draft when the discard is declined", async () => {
      dialogServiceMock.confirm.mockResolvedValueOnce(false);
      component.startReorder();
      component.moveUp(third);
      await component.cancelReorder();
      fixture.detectChanges();
      expect(component.reorderMode()).toBe(true);
      expect(rowNames()).toEqual(["First", "Third", "Second"]);
    });

    it("should not ask when cancelling an unchanged order", async () => {
      component.startReorder();
      await component.cancelReorder();
      expect(dialogServiceMock.confirm).not.toHaveBeenCalled();
      expect(component.reorderMode()).toBe(false);
    });

    it("should not ask when leaving the mode after a successful save", async () => {
      component.startReorder();
      component.moveUp(third);
      await component.saveReorder();
      expect(dialogServiceMock.confirm).not.toHaveBeenCalled();
      expect(component.reorderMode()).toBe(false);
    });

    it("should keep the arrows on the priority value's own line", () => {
      component.startReorder();
      fixture.detectChanges();
      // Value and both arrows share one inline-flex cell, so the row does not grow taller.
      const cells: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll(".ca-priority-cell"));
      expect(cells.length).toBe(3);
      expect(cells[0].textContent!.trim()).toContain("10");
      expect(cells[0].querySelectorAll("button.reorder-button").length).toBe(2);
    });
  });

  describe("stale conditions", () => {
    beforeEach(() => {
      policyServiceMock.conditionTypes.set({
        USER_REALM: {
          label: "User realm",
          operators: [{ name: "IN", label: "is one of" }],
          choices: ["sales"]
        }
      });
    });

    it("should not flag a policy whose condition values all still exist", () => {
      const policy: LockoutPolicy = {
        ...samplePolicy,
        conditions: [{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]
      };
      expect(component.hasStaleConditions(policy)).toBe(false);
    });

    it("should flag a policy referencing a value that is gone", () => {
      const policy: LockoutPolicy = {
        ...samplePolicy,
        conditions: [{ condition_type: "USER_REALM", operator: "IN", value: ["sales", "deleted"] }]
      };
      expect(component.hasStaleConditions(policy)).toBe(true);
    });

    it("should render the warning icon only for a flagged row", () => {
      policyServiceMock.policies.set([
        { ...samplePolicy, id: 1, conditions: [{ condition_type: "USER_REALM", operator: "IN", value: ["deleted"] }] },
        { ...samplePolicy, id: 2, name: "Fine", conditions: [] }
      ]);
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll(".ca-stale-condition-icon").length).toBe(1);
    });
  });
});
