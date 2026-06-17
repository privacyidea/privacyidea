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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockDialogService, MockPendingChangesService } from "@testing/mock-services";
import { MockContainerTemplateService } from "@testing/mock-services/mock-container-template-service";
import { ContainerTemplateCopyDialogComponent } from "./container-template-copy-dialog.component";

describe("ContainerTemplateCopyDialogComponent", () => {
  let component: ContainerTemplateCopyDialogComponent;
  let fixture: ComponentFixture<ContainerTemplateCopyDialogComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;
  let dialogRefMock: MockMatDialogRef<ContainerTemplateCopyDialogComponent, string>;

  const INITIAL_NAME = "OriginalTemplate";

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateCopyDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: INITIAL_NAME }
      ]
    }).compileComponents();

    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    // Set up some initial templates in the service
    const templates: ContainerTemplate[] = [
      { name: INITIAL_NAME, container_type: "type1", default: false, template_options: { tokens: [] } },
      { name: "ExistingCopy", container_type: "type1", default: false, template_options: { tokens: [] } }
    ];
    containerTemplateServiceMock.templates.set(templates);

    fixture = TestBed.createComponent(ContainerTemplateCopyDialogComponent);
    dialogRefMock = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<
      ContainerTemplateCopyDialogComponent,
      string
    >;
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize with the name from MAT_DIALOG_DATA", () => {
    expect(component.template().name).toBe(INITIAL_NAME);
    expect(component.isDirty()).toBeFalsy();
  });

  it("should detect name conflicts and disable save", () => {
    component.editName("ExistingCopy");

    expect(component.nameConflict()).toBeTruthy();
    expect(component.canSave()).toBeFalsy();
    expect(component.actions()[0].disabled).toBeTruthy();
  });

  it("should be dirty when name is changed from original", () => {
    component.editName("BrandNewName");

    expect(component.isDirty()).toBeTruthy();
    expect(component.canSave()).toBeTruthy();
  });

  it("should not allow saving if the name is the same as the original", () => {
    // Manually setting it back to original after it was dirty
    component.editName(INITIAL_NAME);

    expect(component.canSave()).toBeFalsy();
  });

  it("should close the dialog with the new name on successful copy", async () => {
    const NEW_NAME = "UniqueCopyName";
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);

    component.editName(NEW_NAME);
    await component.onAction("copy");

    expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalledWith(
      expect.objectContaining({ name: NEW_NAME })
    );
    expect(dialogRefMock.close).toHaveBeenCalledWith(NEW_NAME);
  });

  it("should not close the dialog if service call fails", async () => {
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);

    component.editName("SomeNewName");
    await component.onAction("copy");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("should correctly handle nameErrorMatcher", () => {
    component.editName("ExistingCopy");
    expect(component.nameErrorMatcher.isErrorState()).toBeTruthy();

    component.editName("UniqueName");
    expect(component.nameErrorMatcher.isErrorState()).toBeFalsy();
  });

  it("should trigger copy on onSave call", async () => {
    const spy = jest.spyOn(component, "onAction");
    component.onSave();
    expect(spy).toHaveBeenCalledWith("copy");
  });
});
