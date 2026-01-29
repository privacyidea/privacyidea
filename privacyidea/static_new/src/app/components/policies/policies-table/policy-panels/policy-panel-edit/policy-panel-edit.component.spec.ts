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
import { PolicyPanelEditComponent } from "./policy-panel-edit.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatExpansionModule } from "@angular/material/expansion";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("PolicyPanelEditComponent", () => {
  let component: PolicyPanelEditComponent;
  let fixture: ComponentFixture<PolicyPanelEditComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPanelEditComponent, NoopAnimationsModule, MatExpansionModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyPanelEditComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("existing policy", () => {
    const policyName = "Test Policy";

    beforeEach(() => {
      fixture.componentRef.setInput("policy", { ...policyServiceMock.getEmptyPolicy, name: policyName });
      fixture.detectChanges();
    });

    it("should display the policy name", () => {
      expect(fixture.nativeElement).toBeTruthy();
      const policyNameElement = fixture.nativeElement.querySelector(".policy-name");
      expect(policyNameElement).toBeTruthy();
      expect(policyNameElement.textContent).toContain(policyName);
    });

    it("should select policy on expansion", () => {
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel");
      panel.dispatchEvent(new Event("opened"));
      fixture.detectChanges();
      expect(policyServiceMock.selectPolicyByName).toHaveBeenCalledWith(policyName);
    });
  });

  describe("new policy", () => {
    beforeEach(() => {
      // component.isNew = input(true);
      fixture.componentRef.setInput("isNew", true);
      fixture.detectChanges();
    });

    it("should initialize new policy on expansion", () => {
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel");
      panel.dispatchEvent(new Event("opened"));
      fixture.detectChanges();
      expect(policyServiceMock.initializeNewPolicy).toHaveBeenCalled();
    });
  });
});
