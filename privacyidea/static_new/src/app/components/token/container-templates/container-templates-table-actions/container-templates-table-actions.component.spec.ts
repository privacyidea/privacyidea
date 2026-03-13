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
import { ContainerTemplatesTableActionsComponent } from "./container-templates-table-actions.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { DialogService } from "src/app/services/dialog/dialog.service";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { MockDialogService, MockContainerTemplateService } from "src/testing/mock-services";
import { ContainerTemplateEditDialogComponent } from "../dialogs/container-template-edit-dialog/container-template-edit-dialog.component";
import { ContainerTemplateCopyDialogComponent } from "../dialogs/container-template-copy-dialog/container-template-copy-dialog.component";
import { ContainerTemplateDeleteDialogComponent } from "../dialogs/container-template-delete-dialog/container-template-delete-dialog.component";
import { By } from "@angular/platform-browser";

describe("ContainerTemplatesTableActionsComponent", () => {
  let component: ContainerTemplatesTableActionsComponent;
  let fixture: ComponentFixture<ContainerTemplatesTableActionsComponent>;
  let dialogServiceMock: MockDialogService;
  let containerTemplateServiceMock: MockContainerTemplateService;

  const mockTemplates = [
    { name: "Template1", container_type: "type1" },
    { name: "Template2", container_type: "type2" }
  ] as any[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplatesTableActionsComponent, NoopAnimationsModule],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplatesTableActionsComponent);
    component = fixture.componentInstance;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;

    // Default input
    fixture.componentRef.setInput("selectedTemplates", []);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should disable Copy and Delete buttons when no templates are selected", () => {
    const buttons = fixture.debugElement.queryAll(By.css("button"));
    // Create is always enabled, Copy (index 1) and Delete (index 2) should be disabled
    expect(buttons[1].nativeElement.disabled).toBeTruthy();
    expect(buttons[2].nativeElement.disabled).toBeTruthy();
  });

  it("should enable Copy and Delete buttons when templates are selected", () => {
    fixture.componentRef.setInput("selectedTemplates", [mockTemplates[0]]);
    fixture.detectChanges();

    const buttons = fixture.debugElement.queryAll(By.css("button"));
    expect(buttons[1].nativeElement.disabled).toBeFalsy();
    expect(buttons[2].nativeElement.disabled).toBeFalsy();
  });

  it("should open ContainerTemplateEditDialogComponent when Create is clicked", () => {
    const spy = jest.spyOn(dialogServiceMock, "openDialog");
    component.openNewTemplateDialog();

    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        component: ContainerTemplateEditDialogComponent
      })
    );
  });

  it("should open Copy dialog and call service for each selected template", async () => {
    fixture.componentRef.setInput("selectedTemplates", mockTemplates);
    fixture.detectChanges();

    const dialogSpy = jest
      .spyOn(dialogServiceMock, "openDialogAsync")
      .mockResolvedValueOnce("Template1_Copy")
      .mockResolvedValueOnce("Template2_Copy");
    const serviceSpy = jest.spyOn(containerTemplateServiceMock, "copyTemplate");

    await component.openCopyTemplateDialog();

    expect(dialogSpy).toHaveBeenCalledTimes(2);
    expect(dialogSpy).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        component: ContainerTemplateCopyDialogComponent,
        data: "Template1"
      })
    );
    expect(serviceSpy).toHaveBeenCalledTimes(2);
    expect(serviceSpy).toHaveBeenCalledWith(mockTemplates[0], "Template1_Copy");
  });

  it("should not call copyTemplate if dialog is cancelled or name is unchanged", async () => {
    fixture.componentRef.setInput("selectedTemplates", [mockTemplates[0]]);
    fixture.detectChanges();

    jest.spyOn(dialogServiceMock, "openDialogAsync").mockResolvedValue(null);
    const serviceSpy = jest.spyOn(containerTemplateServiceMock, "copyTemplate");

    await component.openCopyTemplateDialog();

    expect(serviceSpy).not.toHaveBeenCalled();
  });

  it("should open Delete dialog and call service for each selected template if confirmed", async () => {
    fixture.componentRef.setInput("selectedTemplates", mockTemplates);
    fixture.detectChanges();

    const dialogSpy = jest.spyOn(dialogServiceMock, "openDialogAsync").mockResolvedValue(true);
    const serviceSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplates");

    await component.openDeleteTemplateDialog();

    expect(dialogSpy).toHaveBeenCalledTimes(1);
    expect(dialogSpy).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        component: ContainerTemplateDeleteDialogComponent,
        data: mockTemplates
      })
    );
    expect(serviceSpy).toHaveBeenCalledTimes(1);
    expect(serviceSpy).toHaveBeenCalledWith(["Template1", "Template2"]);
  });

  it("should not call deleteTemplate if deletion is not confirmed", async () => {
    fixture.componentRef.setInput("selectedTemplates", [mockTemplates[0]]);
    fixture.detectChanges();

    jest.spyOn(dialogServiceMock, "openDialogAsync").mockResolvedValue(false);
    const serviceSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplate");

    await component.openDeleteTemplateDialog();

    expect(serviceSpy).not.toHaveBeenCalled();
  });
});
