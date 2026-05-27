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
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockContentService, MockDialogService, MockPendingChangesService } from "@testing/mock-services";
import { MockContainerTemplateService } from "@testing/mock-services/mock-container-template-service";
import { of } from "rxjs";
import { ContainerTemplateEditPageComponent } from "./container-template-edit-page.component";

describe("ContainerTemplateEditPageComponent", () => {
  let component: ContainerTemplateEditPageComponent;
  let fixture: ComponentFixture<ContainerTemplateEditPageComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;
  let contentService: MockContentService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: ContentService, useClass: MockContentService },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({})) } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditPageComponent);
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    contentService.routeUrl.set(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    router = TestBed.inject(Router);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly compute isDirty when template is modified", () => {
    expect(component.isDirty()).toBeFalsy();
    component.template.update((t) => ({ ...t, name: "New Name" }));
    expect(component.isDirty()).toBeTruthy();
  });

  it("should detect name conflicts using the service", () => {
    const existing = { name: "Conflict" };
    containerTemplateServiceMock.templates.set([existing as any]);

    component.template.update((t) => ({ ...t, name: "Conflict" }));

    expect(component.nameConflict()).toBeTruthy();
    expect(component.canSave()).toBeFalsy();
  });

  it("should add a token to the template signal", () => {
    const initialCount = component.template().template_options.tokens.length;
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: [...t.template_options.tokens, { type: "totp" } as any] }
    }));
    expect(component.template().template_options.tokens.length).toBe(initialCount + 1);
    expect((component.template().template_options.tokens[initialCount] as any).type).toBe("totp");
  });

  it("should update a specific token by index", () => {
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: [{ type: "hotp" } as any] }
    }));
    component.template.update((t) => {
      const tokens = [...t.template_options.tokens];
      tokens[0] = { ...tokens[0], description: "Updated" } as any;
      return { ...t, template_options: { tokens } };
    });
    expect((component.template().template_options.tokens[0] as any).description).toBe("Updated");
  });

  it("should remove a token by index", () => {
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: [{ type: "hotp" } as any] }
    }));
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: t.template_options.tokens.filter((_, i) => i !== 0) }
    }));
    expect(component.template().template_options.tokens.length).toBe(0);
  });

  it("should navigate back after successful save", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl");
    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);

    component.template.update((t) => ({ ...t, name: "ValidName" }));
    await component.onAction("save");

    expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES);
  });

  it("should delete the old template name if name was renamed during edit", async () => {
    const oldData = { name: "OldName", container_type: "type1", template_options: { tokens: [] }, default: false };
    component.initTemplate.set(oldData);
    component.template.update((t) => ({ ...t, name: "NewName" }));

    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);
    const deleteSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplate");

    await component.onAction("save");

    expect(deleteSpy).toHaveBeenCalledWith("OldName");
    expect(jest.spyOn(router, "navigateByUrl")).toHaveBeenCalled();
  });

  it("should not navigate if saving the template fails", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl");
    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);

    await component.onAction("save");

    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("should navigate back when onCancel is called and not dirty", () => {
    const pendingChangesService = TestBed.inject(PendingChangesService);
    const clearAllSpy = jest.spyOn(pendingChangesService, "clearAllRegistrations");
    const navigateSpy = jest.spyOn(router, "navigateByUrl");
    expect(component.isDirty()).toBeFalsy();
    component.onCancel();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    expect(clearAllSpy).toHaveBeenCalled();
  });

  it("should open confirmation dialog when onCancel is called and dirty", () => {
    component.template.update((t) => ({ ...t, name: "Changed Name" }));
    expect(component.isDirty()).toBeTruthy();

    const dialogService = TestBed.inject(DialogService);
    const openDialogSpy = jest.spyOn(dialogService, "openDialog");

    component.onCancel();

    expect(openDialogSpy).toHaveBeenCalled();
  });

  it("should call pendingChangesService.save and navigate on save-exit choice in onCancel dialog", async () => {
    const pendingChangesService = TestBed.inject(PendingChangesService);
    const saveSpy = jest.spyOn(pendingChangesService, "save").mockReturnValue(true as any);
    const clearAllSpy = jest.spyOn(pendingChangesService, "clearAllRegistrations");
    const navigateSpy = jest.spyOn(router, "navigateByUrl");

    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    component.template.update((t) => ({ ...t, name: "DirtyName" }));

    const dialogService = TestBed.inject(DialogService);
    const openDialogSpy = jest.spyOn(dialogService, "openDialog");
    component.onCancel();

    const dialogRef = openDialogSpy.mock.results[0].value;
    dialogRef.close("save-exit");

    await Promise.resolve();

    expect(saveSpy).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    expect(clearAllSpy).toHaveBeenCalled();
  });

  it("isNewTemplate is true when no initTemplate is set", () => {
    expect(component.isNewTemplate()).toBe(true);
  });

  it("isNewTemplate is false when initTemplate is set", () => {
    component.initTemplate.set({
      name: "Existing",
      container_type: "generic",
      default: false,
      template_options: { tokens: [] }
    });
    expect(component.isNewTemplate()).toBe(false);
  });

  it("nameInvalidPattern is false for valid names (letters, digits, dots, dashes, underscores)", () => {
    component.template.update((t) => ({ ...t, name: "valid-Name_1.0" }));
    expect(component.nameInvalidPattern()).toBe(false);
  });

  it("nameInvalidPattern is true when name contains special characters", () => {
    component.template.update((t) => ({ ...t, name: "invalid name!" }));
    expect(component.nameInvalidPattern()).toBe(true);
  });

  it("nameInvalidPattern is true for names with spaces", () => {
    component.template.update((t) => ({ ...t, name: "has space" }));
    expect(component.nameInvalidPattern()).toBe(true);
  });

  it("nameErrorMatcher.isErrorState returns true on name conflict", () => {
    containerTemplateServiceMock.templates.set([
      { name: "Taken", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    component.template.update((t) => ({ ...t, name: "Taken" }));
    expect(component.nameErrorMatcher.isErrorState()).toBe(true);
  });

  it("nameErrorMatcher.isErrorState returns true when pattern is invalid and name is non-empty", () => {
    component.template.update((t) => ({ ...t, name: "bad!" }));
    expect(component.nameErrorMatcher.isErrorState()).toBe(true);
  });

  it("nameErrorMatcher.isErrorState returns false for empty name (pattern not flagged)", () => {
    component.template.update((t) => ({ ...t, name: "" }));
    expect(component.nameErrorMatcher.isErrorState()).toBe(false);
  });

  it("actions contains a Save action that is disabled when there is a name conflict", () => {
    containerTemplateServiceMock.templates.set([
      { name: "Taken", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    component.template.update((t) => ({ ...t, name: "Taken" }));
    const save = component.actions().find((a) => a.value === "save")!;
    expect(save).toBeDefined();
    expect(save.disabled).toBe(true);
  });

  it("actions Save action is not disabled when name is valid and no conflict exists", () => {
    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    containerTemplateServiceMock.templates.set([]);
    component.template.update((t) => ({ ...t, name: "UniqueValid" }));
    const save = component.actions().find((a) => a.value === "save")!;
    expect(save.disabled).toBe(false);
  });

  it("should not call deleteTemplate when save fails even if template was renamed", async () => {
    const oldData = { name: "OldName", container_type: "type1", template_options: { tokens: [] }, default: false };
    component.initTemplate.set(oldData);
    component.template.update((t) => ({ ...t, name: "NewName" }));

    jest.spyOn(containerTemplateServiceMock, "canSaveTemplate").mockReturnValue(true);
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);
    const deleteSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplate");

    await component.onAction("save");

    expect(deleteSpy).not.toHaveBeenCalled();
  });
});
