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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../../testing/mock-services/mock-policies-service";
import { PolicyService, PolicyDetail } from "../../../../../../services/policies/policies.service";
import { PolicyPriorityEditComponent } from "./policy-priority-edit.component";

describe("PolicyPriorityEditComponent", () => {
  let component: PolicyPriorityEditComponent;
  let fixture: ComponentFixture<PolicyPriorityEditComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPriorityEditComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyPriorityEditComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
    fixture.componentRef.setInput("editMode", true);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update policy priority on input", () => {
    const priority = 10;
    component.updatePolicyPriority(priority);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ priority });
  });
  const policyDetail: PolicyDetail = {
    action: {
      action1: "value1",
      action2: "value2"
    },
    name: "",
    priority: 10,
    active: false,
    adminrealm: [],
    adminuser: [],
    check_all_resolvers: false,
    client: [],
    conditions: [],
    description: null,
    pinode: [],
    realm: [],
    resolver: [],
    scope: "",
    time: "",
    user: [],
    user_agents: [],
    user_case_insensitive: false
  };
  describe("editMode = false", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("editMode", false);
      policyServiceMock.selectedPolicy.set(policyDetail);
      fixture.detectChanges();
    });

    it("should display the priority as text", () => {
      const html = fixture.nativeElement.innerHTML;
      expect(html).toContain(policyDetail.priority.toString());
    });
  });

  describe("editMode = true", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("editMode", true);
      const policyDetail: PolicyDetail = {
        action: {
          action1: "value1",
          action2: "value2"
        },
        name: "",
        priority: 10,
        active: false,
        adminrealm: [],
        adminuser: [],
        check_all_resolvers: false,
        client: [],
        conditions: [],
        description: null,
        pinode: [],
        realm: [],
        resolver: [],
        scope: "",
        time: "",
        user: [],
        user_agents: [],
        user_case_insensitive: false
      };

      policyServiceMock.selectedPolicy.set(policyDetail);
      fixture.detectChanges();
    });

    it("should display an input field", () => {
      const inputEl = fixture.nativeElement.querySelector("input");
      expect(inputEl).toBeTruthy();
      expect(inputEl.value).toBe("10");
    });

    it("should call updatePolicyPriority when the input value changes", async () => {
      const spy = jest.spyOn(component, "updatePolicyPriority");
      const inputEl = fixture.nativeElement.querySelector("input");
      inputEl.value = "20";
      inputEl.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      expect(spy).toHaveBeenCalledWith(20);
    });
  });
});
