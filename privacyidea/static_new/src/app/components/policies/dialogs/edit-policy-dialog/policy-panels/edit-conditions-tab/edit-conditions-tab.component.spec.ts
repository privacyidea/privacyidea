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
import { EditConditionsTabComponent } from "./edit-conditions-tab.component";
import { PolicyService } from "../../../../../../services/policies/policies.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { Component, input, output } from "@angular/core";
import { By } from "@angular/platform-browser";

@Component({ selector: "app-edit-admin-conditions", standalone: true, template: "" })
class MockAdminComp {
  policy = input.required<any>();
  policyEdit = output<any>();
}

@Component({ selector: "app-edit-user-conditions", standalone: true, template: "" })
class MockUserComp {
  policy = input.required<any>();
  policyEdit = output<any>();
}

@Component({ selector: "app-edit-environment-conditions", standalone: true, template: "" })
class MockEnvComp {
  policy = input.required<any>();
  policyEdit = output<any>();
}

@Component({ selector: "app-edit-additional-conditions", standalone: true, template: "" })
class MockAddComp {
  policy = input.required<any>();
  policyEdit = output<any>();
}

describe("EditConditionsTabComponent", () => {
  let component: EditConditionsTabComponent;
  let fixture: ComponentFixture<EditConditionsTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditConditionsTabComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    })
      .overrideComponent(EditConditionsTabComponent, {
        set: { imports: [MockAdminComp, MockUserComp, MockEnvComp, MockAddComp] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(EditConditionsTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", { scope: "user" });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should toggle admin conditions based on scope", () => {
    expect(fixture.debugElement.query(By.directive(MockAdminComp))).toBeNull();
    fixture.componentRef.setInput("policy", { scope: "admin" });
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.directive(MockAdminComp))).toBeTruthy();
  });

  it("should emit policyEdit", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    const userComp = fixture.debugElement.query(By.directive(MockUserComp)).componentInstance;
    userComp.policyEdit.emit({ realm: ["test"] });
    expect(spy).toHaveBeenCalledWith({ realm: ["test"] });
  });
});
