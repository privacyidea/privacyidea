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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { PolicyEditPageComponent } from "@components/policies/policy-edit-page/policy-edit-page.component";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import {
  MockContentService,
  MockNotificationService,
  MockPendingChangesService,
  MockPolicyService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of } from "rxjs";

/**
 * The page with its real panel, action tab, added-actions list and action rows: an added action whose value does not
 * suit it blocks the save and never reaches the saved policy.
 */
describe("PolicyEditPageComponent – added action validity", () => {
  let fixture: ComponentFixture<PolicyEditPageComponent>;
  let component: PolicyEditPageComponent;
  let policyService: MockPolicyService;

  const stored = (): PolicyDetail => ({
    ...policyService.getEmptyPolicy(),
    name: "limits",
    scope: "enrollment",
    priority: 1,
    action: { max_token_per_user: "5" }
  });

  const numberInput = (): HTMLInputElement =>
    fixture.nativeElement.querySelector("app-policy-action-item-edit input[type=number]");
  const saveButton = (): HTMLButtonElement =>
    fixture.debugElement.query(By.css(".sticky-controls .action-button-primary")).nativeElement;
  const settle = async (): Promise<void> => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const typeNumber = async (value: string): Promise<void> => {
    numberInput().value = value;
    numberInput().dispatchEvent(new Event("input"));
    await settle();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyEditPageComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of({ get: (key: string) => (key === "name" ? "limits" : null) }) }
        },
        { provide: Router, useValue: { navigateByUrl: jest.fn(), events: of(), url: ROUTE_PATHS.POLICIES } },
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    policyService.allPolicies.set([stored()]);
    policyService.getDetailsOfAction.mockReturnValue({ type: "int", desc: "Maximum number of tokens." });
    fixture = TestBed.createComponent(PolicyEditPageComponent);
    component = fixture.componentInstance;
    await settle();
    await settle();
  });

  it("renders the added action as a number input", () => {
    expect(numberInput().value).toBe("5");
    expect(component.canSave()).toBe(false);
  });

  it("saves a changed number", async () => {
    await typeNumber("7");

    expect(component.canSave()).toBe(true);
    expect(saveButton().disabled).toBe(false);
    expect(component.editedPolicy().action).toEqual({ max_token_per_user: "7" });
  });

  it("blocks the save and flags the row when the number is emptied after another edit", async () => {
    component.addPolicyEdit({ description: "limits per user" });
    await settle();
    expect(component.canSave()).toBe(true);

    await typeNumber("");

    expect(component.canSave()).toBe(false);
    expect(saveButton().disabled).toBe(true);
    expect(fixture.nativeElement.querySelector(".policy-action-item.invalid")).not.toBeNull();
    expect(fixture.nativeElement.querySelector(".policy-action-item mat-error")?.textContent?.trim()).toBe(
      "Value is required."
    );
  });

  it("blocks the save when a changed number is emptied", async () => {
    await typeNumber("7");
    await typeNumber("");

    expect(component.canSave()).toBe(false);
    expect(saveButton().disabled).toBe(true);
  });

  it("allows the save again once the emptied number is corrected", async () => {
    await typeNumber("7");
    await typeNumber("");
    await typeNumber("8");

    expect(component.canSave()).toBe(true);
    expect(saveButton().disabled).toBe(false);
    expect(fixture.nativeElement.querySelector(".policy-action-item mat-error")).toBeNull();
  });

  it("keeps the emptied number and the blocked save when another field changes afterwards", async () => {
    await typeNumber("");

    component.addPolicyEdit({ description: "limits per user" });
    await settle();

    expect(numberInput().value).toBe("");
    expect(component.canSave()).toBe(false);
  });

  it("keeps the emptied number and the blocked save while the conditions tab is open", async () => {
    component.addPolicyEdit({ description: "limits per user" });
    await settle();
    await typeNumber("");

    component.activeTab.set("conditions");
    await settle();
    expect(numberInput()).toBeNull();
    expect(component.canSave()).toBe(false);

    component.activeTab.set("actions");
    await settle();
    expect(numberInput().value).toBe("");
    expect(fixture.nativeElement.querySelector(".policy-action-item mat-error")?.textContent?.trim()).toBe(
      "Value is required."
    );
    expect(component.canSave()).toBe(false);
  });

  it("keeps showing the emptied number and blocking the save while the action filter matches nothing", async () => {
    component.addPolicyEdit({ description: "limits per user" });
    await settle();
    await typeNumber("");

    component.actionFilter.set("no such action");
    await settle();

    expect(numberInput().value).toBe("");
    expect(component.canSave()).toBe(false);
  });

  it("forgets the emptied number of a removed action", async () => {
    component.addPolicyEdit({ description: "limits per user" });
    await settle();
    await typeNumber("");

    component.addPolicyEdit({ action: {} });
    await settle();

    expect(numberInput()).toBeNull();
    expect(component.canSave()).toBe(true);
  });

  it("never puts an emptied number into the saved payload, neither as an empty text nor as 0", async () => {
    component.addPolicyEdit({ description: "limits per user" });
    await settle();

    await typeNumber("");
    await component.onSave();

    expect(policyService.savePolicyEdits).toHaveBeenCalledTimes(1);
    const saved = policyService.savePolicyEdits.mock.calls[0][1] as PolicyDetail;
    expect(saved.action).toEqual({ max_token_per_user: "5" });
    expect(saved.action).not.toEqual({ max_token_per_user: "" });
    expect(saved.action).not.toEqual({ max_token_per_user: 0 });
  });
});
