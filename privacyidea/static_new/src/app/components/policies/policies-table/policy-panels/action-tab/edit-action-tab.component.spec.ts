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
import { By } from "@angular/platform-browser";
import { AddedActionsListComponent } from "./added-actions-list/added-actions-list.component";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EditActionTabComponent } from "./edit-action-tab.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";
import { PolicyService, PolicyDetail } from "../../../../../services/policies/policies.service";

describe("EditActionTabComponent", () => {
  let component: EditActionTabComponent;
  let fixture: ComponentFixture<EditActionTabComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditActionTabComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EditActionTabComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
    policyServiceMock.isEditMode.set(false);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display actions for a selected policy", () => {
    const policy: PolicyDetail = {
      name: "test-policy",
      scope: "test",
      action: { action1: "value1", action2: "value2" },
      active: false,
      adminrealm: [],
      adminuser: [],
      check_all_resolvers: false,
      client: [],
      conditions: [],
      description: null,
      pinode: [],
      priority: 0,
      realm: [],
      resolver: [],
      time: "",
      user: [],
      user_agents: [],
      user_case_insensitive: false
    };
    policyServiceMock.selectedPolicy.set(policy);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll("app-added-actions-list");
    expect(actionElements.length).toBe(1);
  });

  it("should not display actions if no policy is selected", () => {
    policyServiceMock.selectedPolicy.set(null);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll("app-added-actions-list");
    expect(actionElements.length).toBe(0);
  });

  it("should display app-action-selector when in edit mode", () => {
    policyServiceMock.isEditMode.set(true);
    fixture.detectChanges();
    const actionSelector = fixture.nativeElement.querySelector("app-action-selector");
    expect(actionSelector).toBeTruthy();
  });

  it("should not display app-action-selector when not in edit mode", () => {
    policyServiceMock.isEditMode.set(false);
    fixture.detectChanges();
    const actionSelector = fixture.nativeElement.querySelector("app-action-selector");
    expect(actionSelector).toBeFalsy();
  });

  it("should always display app-action-detail", () => {
    const actionDetail = fixture.nativeElement.querySelector("app-action-detail");
    expect(actionDetail).toBeTruthy();

    policyServiceMock.isEditMode.set(true);
    fixture.detectChanges();
    const actionDetailAfterEditMode = fixture.nativeElement.querySelector("app-action-detail");
    expect(actionDetailAfterEditMode).toBeTruthy();
  });

  it("should correctly transform policy actions into an array", () => {
    const policy: PolicyDetail = {
      name: "test-policy",
      scope: "test",
      action: { action1: "value1", action2: "value2" },
      active: false,
      adminrealm: [],
      adminuser: [],
      check_all_resolvers: false,
      client: [],
      conditions: [],
      description: null,
      pinode: [],
      priority: 0,
      realm: [],
      resolver: [],
      time: "",
      user: [],
      user_agents: [],
      user_case_insensitive: false
    };
    policyServiceMock.selectedPolicy.set(policy);
    fixture.detectChanges();

    const expectedActions = [
      { name: "action1", value: "value1" },
      { name: "action2", value: "value2" }
    ];
    expect(component.actions()).toEqual(expectedActions);

    policyServiceMock.selectedPolicy.set(null);
    fixture.detectChanges();
    expect(component.actions()).toEqual([]);
  });

  it("should pass the correct actions to app-added-actions-list", () => {
    const policy: PolicyDetail = {
      name: "test-policy",
      scope: "test",
      action: { action1: "value1", action2: "value2" },
      active: false,
      adminrealm: [],
      adminuser: [],
      check_all_resolvers: false,
      client: [],
      conditions: [],
      description: null,
      pinode: [],
      priority: 0,
      realm: [],
      resolver: [],
      time: "",
      user: [],
      user_agents: [],
      user_case_insensitive: false
    };
    policyServiceMock.selectedPolicy.set(policy);
    fixture.detectChanges();

    const selectedActionsListDebugElement = fixture.debugElement.query(By.directive(AddedActionsListComponent));
    expect(selectedActionsListDebugElement).toBeTruthy();

    const selectedActionsListComponent = selectedActionsListDebugElement.componentInstance;
    expect(selectedActionsListComponent.actions()).toEqual(component.actions());
  });
});
