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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatExpansionModule } from "@angular/material/expansion";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ContainerTemplateService } from "../../../../../services/container-template/container-template.service";
import { MockContainerTemplateService } from "../../../../../../testing/mock-services/mock-container-template-service";
import { ContainerTemplateNewComponent } from "./container-template-new.component";
import { HarnessLoader } from "@angular/cdk/testing";
import { TestbedHarnessEnvironment } from "@angular/cdk/testing/testbed";
import { MatExpansionPanelHarness } from "@angular/material/expansion/testing";

describe("ContainerTemplateNewComponent", () => {
  let component: ContainerTemplateNewComponent;
  let fixture: ComponentFixture<ContainerTemplateNewComponent>;
  let templateServiceMock: MockContainerTemplateService;
  let loader: HarnessLoader;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateNewComponent, NoopAnimationsModule, MatExpansionModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateNewComponent);
    templateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    component = fixture.componentInstance;
    loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should not be in edit mode initially", () => {
    expect(component.isEditMode()).toBeFalsy();
  });

  it("should enter edit mode on expansion", () => {
    component.handleExpansion();
    expect(component.isEditMode()).toBeTruthy();
  });

  it("should save template", () => {
    jest.spyOn(templateServiceMock, "postTemplateEdits");
    jest.spyOn(component, "canSaveTemplate").mockReturnValue(true);
    component.saveTemplate();
    expect(templateServiceMock.postTemplateEdits).toHaveBeenCalled();
  });

  it("should not save template if it is not valid", () => {
    jest.spyOn(templateServiceMock, "postTemplateEdits");
    jest.spyOn(component, "canSaveTemplate").mockReturnValue(false);
    component.saveTemplate();
    expect(templateServiceMock.postTemplateEdits).not.toHaveBeenCalled();
  });

  it("should add a token", () => {
    component.isEditMode.set(true);
    const initialTokens = component.newTemplate().template_options.tokens.length;
    component.onAddToken("hotp");
    const newTokens = component.newTemplate().template_options.tokens.length;
    expect(newTokens).toBe(initialTokens + 1);
    expect(component.newTemplate().template_options.tokens[initialTokens].type).toBe("hotp");
  });

  it("should delete a token", () => {
    component.isEditMode.set(true);
    component.onAddToken("hotp");
    const initialTokens = component.newTemplate().template_options.tokens.length;
    component.onDeleteToken(0);
    const newTokens = component.newTemplate().template_options.tokens.length;
    expect(newTokens).toBe(initialTokens - 1);
  });

  it("should handle collapse and keep panel open if changes are not discarded", async () => {
    jest.spyOn(window, "confirm").mockReturnValue(false);
    const panel = await loader.getHarness(MatExpansionPanelHarness);
    await panel.expand();
    component.onNameChange("new name");
    fixture.detectChanges();
    expect(component.isTemplateEdited()).toBeTruthy();
    await panel.collapse();
    expect(component.isEditMode()).toBeTruthy();
    expect(await panel.isExpanded()).toBeTruthy();
  });

  it("should delete template", () => {
    jest.spyOn(window, "confirm").mockReturnValue(true);
    jest.spyOn(templateServiceMock, "deleteTemplate");
    component.deleteTemplate("test");
    expect(templateServiceMock.deleteTemplate).toHaveBeenCalledWith("test");
  });

  it("should not delete template if not confirmed", () => {
    jest.spyOn(window, "confirm").mockReturnValue(false);
    jest.spyOn(templateServiceMock, "deleteTemplate");
    component.deleteTemplate("test");
    expect(templateServiceMock.deleteTemplate).not.toHaveBeenCalled();
  });

  it("should cancel edit mode", () => {
    jest.spyOn(window, "confirm").mockReturnValue(true);
    component.isEditMode.set(true);
    component.onNameChange("new name");
    component.cancelEditMode();
    expect(component.isEditMode()).toBeFalsy();
  });

  it("should not cancel edit mode if not confirmed", () => {
    jest.spyOn(window, "confirm").mockReturnValue(false);
    component.isEditMode.set(true);
    component.onNameChange("new name");
    component.cancelEditMode();
    expect(component.isEditMode()).toBeTruthy();
  });

  it("should change name", () => {
    component.isEditMode.set(true);
    component.onNameChange("new name");
    expect(component.newTemplate().name).toBe("new name");
  });

  it("should change type", () => {
    component.isEditMode.set(true);
    component.onTypeChange("new type" as any);
    expect(component.newTemplate().container_type).toBe("new type");
  });

  it("should toggle default", () => {
    component.isEditMode.set(true);
    const initialDefault = component.newTemplate().default;
    component.onDefaultToggle();
    expect(component.newTemplate().default).toBe(!initialDefault);
  });

  it("should edit token", () => {
    component.isEditMode.set(true);
    component.onAddToken("hotp");
    component.onEditToken({ description: "new description" }, 0);
    expect(component.newTemplate().template_options.tokens[0].description).toBe("new description");
  });
});
