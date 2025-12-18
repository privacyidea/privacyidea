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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AddedActionsListComponent } from "./added-actions-list.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";

describe("AddedActionsListComponent", () => {
  let component: AddedActionsListComponent;
  let fixture: ComponentFixture<AddedActionsListComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddedActionsListComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(AddedActionsListComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
    fixture.componentRef.setInput("actions", []);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of actions", () => {
    const actions = [
      { name: "action1", value: "value1" },
      { name: "action2", value: "value2" }
    ];
    fixture.componentRef.setInput("actions", actions);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll(".action-card");
    expect(actionElements.length).toBe(actions.length);
  });

  it("should select an action on click", () => {
    const actions = [{ name: "action1", value: "value1" }];
    fixture.componentRef.setInput("actions", actions);
    fixture.detectChanges();

    const actionElement = fixture.nativeElement.querySelector(".action-card");
    actionElement.click();

    const selectedAction = policyServiceMock.selectedAction();
    expect(selectedAction).toBe(actions[0]);
  });
});
