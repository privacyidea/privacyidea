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
import { PoliciesComponent } from "./policies.component";
import { PolicyDetail, PolicyService } from "../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { PolicyPanelComponent } from "./policy-panels/policy-panel/policy-panel.component";
import { MockPolicyService } from "../../../testing/mock-services/mock-policies-service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("PoliciesComponent", () => {
  let component: PoliciesComponent;
  let fixture: ComponentFixture<PoliciesComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesComponent, NoopAnimationsModule, PolicyPanelComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PoliciesComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of policies", () => {
    const policies: PolicyDetail[] = [
      { ...policyServiceMock.emptyPolicy, name: "policy1", scope: "test" },
      { ...policyServiceMock.emptyPolicy, name: "policy2", scope: "test" }
    ];
    policyServiceMock.allPolicies.set(policies);
    fixture.detectChanges();

    const policyElements = fixture.nativeElement.querySelectorAll(".list-card");
    expect(policyElements.length).toBe(policies.length + 1); // +1 for the "new policy" panel
    expect(policyElements[1].textContent).toContain("policy1");
    expect(policyElements[2].textContent).toContain("policy2");
  });

  it("should display a new policy panel", () => {
    fixture.detectChanges();
    const newPolicyPanel = fixture.nativeElement.querySelector(".list-card");
    expect(newPolicyPanel).toBeTruthy();
    expect(newPolicyPanel.textContent).toContain("New Policy");
  });
});
