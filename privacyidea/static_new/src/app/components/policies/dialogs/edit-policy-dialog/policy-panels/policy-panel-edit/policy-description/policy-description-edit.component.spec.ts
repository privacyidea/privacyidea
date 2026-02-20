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
import { PolicyDescriptionEditComponent } from "./policy-description-edit.component";
import { FormsModule } from "@angular/forms";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { DocumentationService } from "../../../../../../../services/documentation/documentation.service";
import { MockDocumentationService } from "src/testing/mock-services/mock-documentation-service";

describe("PolicyDescriptionEditComponent", () => {
  let component: PolicyDescriptionEditComponent;
  let fixture: ComponentFixture<PolicyDescriptionEditComponent>;
  let docService: MockDocumentationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyDescriptionEditComponent, FormsModule, NoopAnimationsModule],
      providers: [{ provide: DocumentationService, useClass: MockDocumentationService }]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyDescriptionEditComponent);
    component = fixture.componentInstance;
    docService = TestBed.inject(DocumentationService) as unknown as MockDocumentationService;
    fixture.componentRef.setInput("description", "Initial description");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit descriptionChange when updatePolicyDescription is called", () => {
    const spy = jest.spyOn(component.descriptionChange, "emit");
    component.updatePolicyDescription("Updated description");
    expect(spy).toHaveBeenCalledWith("Updated description");
  });

  it("should call documentationService when openDocumentation is called", () => {
    const spy = jest.spyOn(docService, "openDocumentation");
    component.openDocumentation("test-page");
    expect(spy).toHaveBeenCalledWith("test-page");
  });
});
