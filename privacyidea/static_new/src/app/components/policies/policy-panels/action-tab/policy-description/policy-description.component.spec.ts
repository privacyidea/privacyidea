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
import { PolicyDescriptionComponent } from "./policy-description.component";
import { DocumentationService } from "../../../../../services/documentation/documentation.service";
import { PolicyDetail, PolicyService } from "../../../../../services/policies/policies.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";
import { MockDocumentationService } from "../../../../../../testing/mock-services/mock-documentation-service";
import "@angular/localize/init";

describe("PolicyDescriptionComponent", () => {
  let component: PolicyDescriptionComponent;
  let fixture: ComponentFixture<PolicyDescriptionComponent>;
  let policyServiceMock: MockPolicyService;
  let documentationServiceMock: MockDocumentationService;
  const policyDetail: PolicyDetail = {
    action: null,
    active: true,
    adminrealm: [],
    adminuser: [],
    check_all_resolvers: false,
    client: [],
    conditions: [],
    description: "test description",
    name: "test-policy",
    pinode: [],
    priority: 1,
    realm: [],
    resolver: [],
    scope: "",
    time: "",
    user: [],
    user_agents: [],
    user_case_insensitive: false
  };
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyDescriptionComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DocumentationService, useClass: MockDocumentationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyDescriptionComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    documentationServiceMock = TestBed.inject(DocumentationService) as unknown as MockDocumentationService;
    component = fixture.componentInstance;
    policyServiceMock.isEditMode.set(false);

    policyServiceMock.selectedPolicy.set(policyDetail);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update policy description on input", () => {
    const description = "new test description";
    component.updatePolicyDescription(description);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ description });
  });

  it("should open documentation on button click", () => {
    const page = "test-page";
    component.openDocumentation(page);
    expect(documentationServiceMock.openDocumentation).toHaveBeenCalledWith(page);
  });

  describe("non-edit mode", () => {
    beforeEach(() => {
      policyServiceMock.isEditMode.set(false);
      fixture.detectChanges();
    });

    it("should display the description when available", () => {
      const html = fixture.nativeElement.innerHTML;
      expect(html).toContain(policyDetail.description);
    });

    it("should not display the description section when description is null", () => {
      policyServiceMock.selectedPolicy.set({
        ...policyServiceMock.selectedPolicy()!,
        description: null
      });
      fixture.detectChanges();
      const descriptionContainer = fixture.nativeElement.querySelector(".action-description-container");
      expect(descriptionContainer).toBeFalsy();
    });
  });

  describe("edit mode", () => {
    beforeEach(() => {
      policyServiceMock.isEditMode.set(true);
      fixture.detectChanges();
    });

    it("should display a textarea", () => {
      const textareaEl = fixture.nativeElement.querySelector("textarea");
      expect(textareaEl).toBeTruthy();
      expect(textareaEl.value).toBe("test description");
    });

    it("should have the correct placeholder", () => {
      const textareaEl = fixture.nativeElement.querySelector("textarea");
      expect(textareaEl.placeholder).toBe("(optional) Enter a description for this policy...");
    });

    it("should call updatePolicyDescription when textarea value changes", async () => {
      const spy = jest.spyOn(component, "updatePolicyDescription");
      const textareaEl = fixture.nativeElement.querySelector("textarea");
      textareaEl.value = "updated description";
      textareaEl.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      expect(spy).toHaveBeenCalledWith("updated description");
    });
  });
});
