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
import { EditEnvironmentConditionsComponent } from "./edit-environment-conditions.component";
import { PolicyService } from "../../../../../../../services/policies/policies.service";
import { SystemService } from "../../../../../../../services/system/system.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { MockSystemService } from "src/testing/mock-services/mock-system-service";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { ReactiveFormsModule } from "@angular/forms";
import { By } from "@angular/platform-browser";

describe("EditEnvironmentConditionsComponent", () => {
  let component: EditEnvironmentConditionsComponent;
  let fixture: ComponentFixture<EditEnvironmentConditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditEnvironmentConditionsComponent, ReactiveFormsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: SystemService, useClass: MockSystemService },
        provideNoopAnimations()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EditEnvironmentConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", {
      name: "test-policy",
      user_agents: ["PAM"],
      time: "Mon-Fri: 9-18",
      client: ["10.0.0.0/8"]
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form controls with policy values", () => {
    expect(component.validTimeFormControl.value).toBe("Mon-Fri: 9-18");
    expect(component.clientFormControl.value).toBe("10.0.0.0/8");
  });

  it("should validate client format correctly", () => {
    component.clientFormControl.setValue("invalid-ip");
    expect(component.clientFormControl.invalid).toBe(true);

    component.clientFormControl.setValue("192.168.1.1");
    expect(component.clientFormControl.valid).toBe(true);
  });

  it("should emit edits when adding a user agent", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.addUserAgentFormControl.setValue("NewAgent");
    component.addUserAgent();
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        user_agents: ["PAM", "NewAgent"]
      })
    );
  });

  it("should clear valid time control", () => {
    component.clearValidTimeControl();
    expect(component.validTimeFormControl.value).toBe("");
  });
});
