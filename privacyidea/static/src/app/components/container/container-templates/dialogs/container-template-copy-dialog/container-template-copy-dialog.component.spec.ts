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
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
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

  const nameInput = (): HTMLInputElement => fixture.nativeElement.querySelector("input");
  const errors = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) => (e as HTMLElement).textContent!.trim());
  // Types into the name input the way a user does, so the field becomes dirty.
  const type = (name: string): void => {
    nameInput().value = name;
    nameInput().dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("closing with unsaved changes", () => {
    const clickCloseButton = () => {
      const closeButton: HTMLButtonElement = fixture.nativeElement.querySelector(".pi-dialog-footer button");
      expect(closeButton.textContent?.trim()).toBe("Cancel");
      closeButton.click();
      fixture.detectChanges();
    };

    it("asks before discarding an edited name instead of closing right away", () => {
      const dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      type("RenamedTemplate");

      clickCloseButton();

      expect(dialogService.openDialogAsync).toHaveBeenCalledWith(
        expect.objectContaining({ component: SaveAndExitDialogComponent })
      );
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("closes without asking when nothing was edited", () => {
      const dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;

      clickCloseButton();

      expect(dialogService.openDialogAsync).not.toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });
  });

  it("should initialize with the name from MAT_DIALOG_DATA", () => {
    expect(component.template().name).toBe(INITIAL_NAME);
    expect(nameInput().value).toBe(INITIAL_NAME);
    expect(component.isDirty()).toBeFalsy();
  });

  it("registers the validity of the name with the pending changes service", () => {
    const pendingChanges = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    expect(pendingChanges.registerValidChanges).toHaveBeenCalledWith(component.canSave);
  });

  it("starts without a copy that can be saved and without an error", () => {
    expect(component.canSave()).toBe(false);
    expect(component.actions()[0].disabled).toBe(true);
    expect(errors()).toEqual([]);
  });

  it("should detect name conflicts, disable save and show the error", () => {
    type("ExistingCopy");

    expect(hasError(component.form.name, ERR.nameTaken)).toBe(true);
    expect(component.canSave()).toBeFalsy();
    expect(component.actions()[0].disabled).toBeTruthy();
    expect(errors()).toEqual(["A template with this name already exists."]);
  });

  it("should be dirty when name is changed from original", () => {
    type("BrandNewName");

    expect(component.isDirty()).toBeTruthy();
    expect(component.canSave()).toBeTruthy();
    expect(component.actions()[0].disabled).toBe(false);
    expect(errors()).toEqual([]);
  });

  it("should not allow saving if the name is the same as the original", () => {
    type("Other");
    type(INITIAL_NAME);

    expect(component.canSave()).toBeFalsy();
    expect(hasError(component.form.name, "notChanged")).toBe(true);
    expect(hasError(component.form.name, ERR.nameTaken)).toBe(false);
    expect(errors()).toEqual(["Template name must be different from the original"]);
  });

  it("requires a name and shows the error once it is emptied", () => {
    type("");

    expect(component.canSave()).toBe(false);
    expect(hasError(component.form.name, ERR.required)).toBe(true);
    expect(errors()).toEqual(["Template name is required"]);
  });

  it.each(["has space", "bad!"])("rejects the name %p for its characters", (name) => {
    type(name);

    expect(component.canSave()).toBe(false);
    expect(hasError(component.form.name, ERR.pattern)).toBe(true);
    expect(errors()).toHaveLength(1);
    expect(errors()[0]).toContain("invalid characters");
  });

  it("copies on Enter only while the name is valid", () => {
    const copySpy = jest.spyOn(component, "onAction").mockResolvedValue();
    const pressEnter = () => nameInput().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

    pressEnter();
    expect(copySpy).not.toHaveBeenCalled();

    type("UniqueName");
    pressEnter();
    expect(copySpy).toHaveBeenCalledWith("copy");
  });

  it("should close the dialog with the new name on successful copy", async () => {
    const NEW_NAME = "UniqueCopyName";
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);

    type(NEW_NAME);
    await component.onAction("copy");

    expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalledWith(
      expect.objectContaining({ name: NEW_NAME })
    );
    expect(dialogRefMock.close).toHaveBeenCalledWith(NEW_NAME);
  });

  it("should not close the dialog if service call fails", async () => {
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);

    type("SomeNewName");
    await component.onAction("copy");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("should trigger copy on onSave call", async () => {
    const spy = jest.spyOn(component, "onAction");
    component.onSave();
    expect(spy).toHaveBeenCalledWith("copy");
  });
});
