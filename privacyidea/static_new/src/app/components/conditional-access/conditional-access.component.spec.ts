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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { ConditionalAccessPolicyService, LockoutPolicy } from "@services/conditional-access/conditional-access-policy.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockAuthService,
  MockConditionalAccessPolicyService,
  MockDialogService,
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
  let dialogClosed: Subject<ConditionalAccessToggleAction | undefined>;
  let router: Router;

  const samplePolicy: LockoutPolicy = {
    id: 1,
    name: "Brute Force",
    time_window_seconds: 600,
    enabled: true,
    dry_run: false,
    priority: 1,
    counter_types_to_track: ["PIN_FAIL"],
    stages: [{ failure_threshold: 5, priority: 1, actions: [] }]
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
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    policyServiceMock.policies.set([samplePolicy]);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
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
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS + samplePolicy.id);
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
        { failure_threshold: 3, priority: 1, actions: [] },
        { failure_threshold: 5, priority: 2, actions: [] }
      ]
    };
    expect(component.thresholdDisplay(multiStage)).toBe("3, 5");
  });

  it("should list every action type across all stages", () => {
    const policy: LockoutPolicy = {
      ...samplePolicy,
      stages: [
        { failure_threshold: 3, priority: 1, actions: [{ action_type: "LOCK_USER", action_value: 60 }] },
        {
          failure_threshold: 5,
          priority: 2,
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
});
