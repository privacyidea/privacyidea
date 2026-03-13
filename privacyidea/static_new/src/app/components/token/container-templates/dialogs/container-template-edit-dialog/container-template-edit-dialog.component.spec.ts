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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ContainerTemplateService } from "../../../../../services/container-template/container-template.service";
import { MockContainerTemplateService } from "../../../../../../testing/mock-services/mock-container-template-service";
import { ContainerTemplateEditDialogComponent } from "./container-template-edit-dialog.component";
import { DialogService } from "src/app/services/dialog/dialog.service";
import { PendingChangesService } from "src/app/services/pending-changes/pending-changes.service";
import { MockDialogService, MockPendingChangesService } from "src/testing/mock-services";
import { MockMatDialogRef } from "src/testing/mock-mat-dialog-ref";

describe("ContainerTemplateEditDialogComponent", () => {
  let component: ContainerTemplateEditDialogComponent;
  let fixture: ComponentFixture<ContainerTemplateEditDialogComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;
  let dialogRefMock: MockMatDialogRef<any>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditDialogComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: null }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditDialogComponent);
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    dialogRefMock = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any>;
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly compute isDirty when template is modified", () => {
    expect(component.isDirty()).toBeFalsy();
    component.editTemplate({ name: "New Name" });
    expect(component.isDirty()).toBeTruthy();
  });

  it("should detect name conflicts using the service", () => {
    const existing = { name: "Conflict" };
    containerTemplateServiceMock.templates.set([existing as any]);

    component.editTemplate({ name: "Conflict" });

    expect(component.nameConflict()).toBeTruthy();
    expect(component.canSave()).toBeFalsy();
  });

  it("should add a token to the template signal", () => {
    const initialCount = component.tokens().length;
    component.onAddToken("totp");
    expect(component.tokens().length).toBe(initialCount + 1);
    expect((component.tokens()[initialCount] as any).type).toBe("totp");
  });

  it("should update a specific token by index", () => {
    component.onAddToken("hotp");
    component.onEditToken({ description: "Updated" }, 0);
    expect((component.tokens()[0] as any).description).toBe("Updated");
  });

  it("should remove a token by index", () => {
    component.onAddToken("hotp");
    component.onDeleteToken(0);
    expect(component.tokens().length).toBe(0);
  });

  it("should close the dialog with the template data on successful save", async () => {
    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);

    component.editTemplate({ name: "ValidName" });
    await component.onAction("save");

    expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(component.template());
  });

  it("should delete the old template name if name was renamed during edit", async () => {
    const oldData = { name: "OldName", container_type: "type1", template_options: { tokens: [] } };
    (component as any).data = oldData;

    component.editTemplate({ name: "NewName" });

    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);
    const deleteSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplate");

    await component.onAction("save");

    expect(deleteSpy).toHaveBeenCalledWith("OldName");
    expect(dialogRefMock.close).toHaveBeenCalled();
  });

  it("should not call close if saving the template fails", async () => {
    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);

    await component.onAction("save");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("should close directly on backdrop click if NOT dirty", () => {
    expect(component.isDirty()).toBeFalsy();
    dialogRefMock.fireBackdropClick();
    expect(dialogRefMock.close).toHaveBeenCalled();
  });

  it("should open confirmation dialog on backdrop click if dirty", async () => {
    component.editTemplate({ name: "Changed Name" });
    expect(component.isDirty()).toBeTruthy();

    const dialogService = TestBed.inject(DialogService);
    const openDialogSpy = jest.spyOn(dialogService, "openDialogAsync").mockResolvedValue("none");

    dialogRefMock.fireBackdropClick();

    expect(dialogRefMock.close).not.toHaveBeenCalled();
    expect(openDialogSpy).toHaveBeenCalled();
  });
});
