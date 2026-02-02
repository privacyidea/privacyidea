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
import { ActionDetailComponent } from "./action-detail.component";
import { PolicyActionDetail, PolicyDetail, PolicyService } from "../../../../../services/policies/policies.service";
import { DocumentationService } from "../../../../../services/documentation/documentation.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockDocumentationService } from "../../../../../../testing/mock-services/mock-documentation-service";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";

describe("ActionDetailComponent", () => {
  let component: ActionDetailComponent;
  let fixture: ComponentFixture<ActionDetailComponent>;
  let policyServiceMock: MockPolicyService;
  let documentationServiceMock: MockDocumentationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ActionDetailComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DocumentationService, useClass: MockDocumentationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ActionDetailComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    documentationServiceMock = TestBed.inject(DocumentationService) as unknown as MockDocumentationService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display documentation and notes", () => {
    const docu = { actionDocu: ["doc1"], actionNotes: ["note1"] };
    documentationServiceMock.policyActionDocumentation.set(docu);
    policyServiceMock.selectedAction.set({ name: "test", value: "" });

    component.toggleContent("docu");
    fixture.detectChanges();
    const docuElement = fixture.nativeElement.querySelector(".action-docu");
    expect(docuElement).toBeTruthy();
    expect(docuElement.textContent).toContain("doc1");

    component.toggleContent("notes");
    fixture.detectChanges();
    const notesElement = fixture.nativeElement.querySelector(".action-notes");
    expect(notesElement).toBeTruthy();
    expect(notesElement.textContent).toContain("note1");
  });

  it("should apply changes when input is valid", () => {
    const policyActionDetail: PolicyActionDetail = {
      desc: "test action detail",
      type: "str"
    };
    policyServiceMock.selectedActionDetail.set(policyActionDetail);
    policyServiceMock.selectedAction.set({ name: "test", value: "value" });
    fixture.detectChanges();

    component.applyChanges();
    expect(policyServiceMock.updateActionInSelectedPolicy).toHaveBeenCalled();
    const selectedAction = policyServiceMock.selectedAction();
    expect(selectedAction).toEqual(null);
  });

  it("should not apply changes when input is invalid", () => {
    const policyActionDetail: PolicyActionDetail = {
      desc: "test action detail",
      type: "str"
    };
    policyServiceMock.selectedActionDetail.set(policyActionDetail);
    policyServiceMock.selectedAction.set({ name: "test", value: "value" });
    fixture.detectChanges();

    jest.spyOn(policyServiceMock, "actionValueIsValid").mockReturnValue(false);

    component.applyChanges();
    expect(policyServiceMock.updateActionInSelectedPolicy).not.toHaveBeenCalled();
  });

  it("should return false from actionIsAlreadyAdded if no action is selected", () => {
    policyServiceMock.selectedAction.set(null);
    fixture.detectChanges();
    expect(component.selectedActionIsAlreadyAdded()).toBe(false);
  });

  it("should return false from actionIsAlreadyAdded if action is not in policy", () => {
    policyServiceMock.selectedAction.set({ name: "newAction", value: "" });
    const policy: PolicyDetail = {
      ...policyServiceMock.getEmptyPolicy,

      action: { existingAction: "value" }
    };
    policyServiceMock.selectedPolicy.set(policy);
    fixture.detectChanges();
    expect(component.selectedActionIsAlreadyAdded()).toBe(false);
  });

  it("should return true from actionIsAlreadyAdded if action is already in policy", () => {
    policyServiceMock.selectedAction.set({ name: "existingAction", value: "" });
    const policy: PolicyDetail = {
      ...policyServiceMock.getEmptyPolicy,
      action: { existingAction: "value" }
    };
    policyServiceMock.selectedPolicy.set(policy);
    fixture.detectChanges();
    expect(component.selectedActionIsAlreadyAdded()).toBe(true);
  });

  it("should compute actionDocuString correctly", () => {
    // Test with value
    const docu = { actionDocu: ["doc1", "doc2"], actionNotes: [] };
    documentationServiceMock.policyActionDocumentation.set(docu);
    fixture.detectChanges();
    expect(component.actionDocuInfo()).toBe("doc1\ndoc2");

    // Test with null
    documentationServiceMock.policyActionDocumentation.set(null);
    fixture.detectChanges();
    expect(component.actionDocuInfo()).toBeUndefined();
  });

  it("should compute actionNotesString correctly", () => {
    // Test with value
    const docu = { actionDocu: [], actionNotes: ["note1", "note2"] };
    documentationServiceMock.policyActionDocumentation.set(docu);
    fixture.detectChanges();
    expect(component.actionDocuNotes()).toBe("note1\nnote2");

    // Test with null
    documentationServiceMock.policyActionDocumentation.set(null);
    fixture.detectChanges();
    expect(component.actionDocuNotes()).toBeUndefined();
  });

  describe("inputIsValid", () => {
    it("should be false if selectedActionDetail is null", () => {
      policyServiceMock.selectedActionDetail.set(null);
      fixture.detectChanges();
      expect(component.inputIsValid()).toBe(false);
    });

    it("should be false if actionValueIsValid returns false", () => {
      policyServiceMock.selectedActionDetail.set({ desc: "test", type: "str" });
      jest.spyOn(policyServiceMock, "actionValueIsValid").mockReturnValue(false);
      fixture.detectChanges();
      expect(component.inputIsValid()).toBe(false);
    });

    it("should be true if actionValueIsValid returns true", () => {
      policyServiceMock.selectedActionDetail.set({ desc: "test", type: "str" });
      jest.spyOn(policyServiceMock, "actionValueIsValid").mockReturnValue(true);
      fixture.detectChanges();
      expect(component.inputIsValid()).toBe(true);
    });
  });
});
