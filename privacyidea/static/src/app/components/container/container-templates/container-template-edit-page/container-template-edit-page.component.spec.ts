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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContainerTemplateDeleteDialogComponent } from "@components/container/container-templates/dialogs/container-template-delete-dialog/container-template-delete-dialog.component";
import { ContainerTemplate } from "@services/container/container.service";
import { ContainerTemplateEditComponent } from "@components/container/container-templates/container-template-edit/container-template-edit.component";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import {
  MockAuthService,
  MockContainerService,
  MockContentService,
  MockDialogService,
  MockNotificationService,
  MockPendingChangesService,
  MockSystemService,
  MockTokenService
} from "@testing/mock-services";
import { MockContainerTemplateService } from "@testing/mock-services/mock-container-template-service";
import { BehaviorSubject, of } from "rxjs";
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
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService },
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

  const hotpToken = { type: "hotp" } as TokenEnrollmentPayload;
  const editComponent = (): ContainerTemplateEditComponent =>
    fixture.debugElement.query(By.directive(ContainerTemplateEditComponent)).componentInstance;
  // Gives the template everything its rules require and lets the edit component pick it up.
  const fillValid = (): void => {
    component.template.update((t) => ({
      ...t,
      name: "ValidName",
      container_type: "generic",
      template_options: { tokens: [hotpToken] }
    }));
    fixture.detectChanges();
    jest.spyOn(editComponent(), "collectTokens").mockReturnValue([hotpToken]);
  };

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly compute isDirty when template is modified", () => {
    expect(component.isDirty()).toBeFalsy();
    component.template.update((t) => ({ ...t, name: "New Name" }));
    expect(component.isDirty()).toBeTruthy();
  });

  it("is not dirty for a new template that starts on the first container type", () => {
    containerTemplateServiceMock.availableContainerTypes.set(["generic", "smartphone"]);
    fixture.detectChanges();

    expect(component.template().container_type).toBe("generic");
    expect(component.isDirty()).toBe(false);

    component.template.update((t) => ({ ...t, container_type: "smartphone" }));
    expect(component.isDirty()).toBe(true);
  });

  it("is not dirty for an unchanged existing template", () => {
    component.initTemplate.set({
      name: "Existing",
      container_type: "generic",
      template_options: { tokens: [hotpToken] },
      default: true
    });

    expect(component.isDirty()).toBe(false);
  });

  it("cannot save a name that another template has", () => {
    fillValid();
    expect(component.canSave()).toBe(true);

    containerTemplateServiceMock.templates.set([{ name: "ValidName" } as ContainerTemplate]);

    expect(component.canSave()).toBe(false);
  });

  it("cannot save before the edit component is mounted", () => {
    const unmounted = TestBed.createComponent(ContainerTemplateEditPageComponent).componentInstance;

    expect(unmounted.canSave()).toBe(false);
  });

  it("enables the Save button once the template is valid", () => {
    const saveButton = (): HTMLButtonElement =>
      fixture.debugElement.queryAll(By.css("button")).find((b) => b.nativeElement.textContent.includes("Save"))!
        .nativeElement;
    expect(saveButton().disabled).toBe(true);

    fillValid();
    fixture.detectChanges();

    expect(saveButton().disabled).toBe(false);
  });

  it("should add a token to the template signal", () => {
    const initialCount = component.template().template_options.tokens.length;
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: [...t.template_options.tokens, { type: "totp" } as TokenEnrollmentPayload] }
    }));
    expect(component.template().template_options.tokens.length).toBe(initialCount + 1);
    expect(component.template().template_options.tokens[initialCount].type).toBe("totp");
  });

  it("should update a specific token by index", () => {
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: [{ type: "hotp" } as TokenEnrollmentPayload] }
    }));
    component.template.update((t) => {
      const tokens = [...t.template_options.tokens];
      tokens[0] = { ...tokens[0], description: "Updated" };
      return { ...t, template_options: { tokens } };
    });
    expect(component.template().template_options.tokens[0].description).toBe("Updated");
  });

  it("should remove a token by index", () => {
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: [{ type: "hotp" } as TokenEnrollmentPayload] }
    }));
    component.template.update((t) => ({
      ...t,
      template_options: { tokens: t.template_options.tokens.filter((_, i) => i !== 0) }
    }));
    expect(component.template().template_options.tokens.length).toBe(0);
  });

  it("should navigate back after successful save", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl");
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);

    fillValid();
    await component.onAction("save");

    expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES);
  });

  it("saving an existing template never deletes a template", async () => {
    const oldData = { name: "OldName", container_type: "type1", template_options: { tokens: [] }, default: false };
    component.initTemplate.set(oldData);
    fillValid();
    component.template.update((t) => ({ ...t, name: "NewName" }));

    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);
    const deleteSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplate");
    const navigateSpy = jest.spyOn(router, "navigateByUrl");

    await component.onAction("save");

    expect(deleteSpy).not.toHaveBeenCalled();
    expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalledWith(
      expect.objectContaining({ name: "OldName" })
    );
    expect(navigateSpy).toHaveBeenCalled();
  });

  it("the template name is read-only for an existing template and editable for a new one", () => {
    const nameInput = () =>
      fixture.nativeElement.querySelector('input[aria-label="Template Name"]') as HTMLInputElement;
    fixture.detectChanges();
    expect(nameInput().readOnly).toBe(false);

    component.initTemplate.set({
      name: "OldName",
      container_type: "generic",
      template_options: { tokens: [] },
      default: false
    });
    fixture.detectChanges();
    expect(nameInput().readOnly).toBe(true);
  });

  it("should not navigate if saving the template fails", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl");
    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);

    fillValid();
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
    const saveSpy = jest.spyOn(pendingChangesService, "save").mockResolvedValue(true);
    const clearAllSpy = jest.spyOn(pendingChangesService, "clearAllRegistrations");
    const navigateSpy = jest.spyOn(router, "navigateByUrl");

    fillValid();

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

  describe("pending changes registration", () => {
    let pendingChanges: MockPendingChangesService;
    const registeredSave = (): (() => Promise<boolean>) => pendingChanges.registerSave.mock.calls[0][0];

    beforeEach(() => {
      pendingChanges = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    });

    it("registers the dirty state and the validity of the template", () => {
      expect(pendingChanges.registerHasChanges).toHaveBeenCalledWith(component.isDirty);
      expect(pendingChanges.registerValidChanges).toHaveBeenCalledWith(component.canSave);
    });

    it("registers a save function that posts the template and stays on the page", async () => {
      const navigateSpy = jest.spyOn(router, "navigateByUrl");
      fillValid();

      await expect(registeredSave()()).resolves.toBe(true);

      expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalledWith(
        expect.objectContaining({ name: "ValidName", container_type: "generic" })
      );
      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("lets the real pending changes service save through the registered function", async () => {
      const real = new PendingChangesService();
      fillValid();
      real.registerSave(registeredSave());

      await expect(real.save()).resolves.toBe(true);
      expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalled();
      real.ngOnDestroy();
    });

    it("reports a failed save", async () => {
      containerTemplateServiceMock.postTemplateEdits.mockResolvedValueOnce(false);
      fillValid();

      await expect(registeredSave()()).resolves.toBe(false);
    });

    it("reports false instead of throwing when the request fails", async () => {
      containerTemplateServiceMock.postTemplateEdits.mockRejectedValueOnce(new Error("boom"));
      fillValid();

      await expect(registeredSave()()).resolves.toBe(false);
    });

    it("does not save an invalid template", async () => {
      await expect(registeredSave()()).resolves.toBe(false);

      expect(containerTemplateServiceMock.postTemplateEdits).not.toHaveBeenCalled();
    });
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

  describe("onSave", () => {
    it("returns true when onAction('save') resolves", async () => {
      jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(true);
      fillValid();

      await expect(component.onSave()).resolves.toBe(true);
    });

    it("returns false when onAction('save') throws", async () => {
      jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockRejectedValue(new Error("boom"));
      fillValid();

      await expect(component.onSave()).resolves.toBe(false);
    });
  });

  it("save aborts and notifies when the edit component reports invalid token configurations", async () => {
    const postSpy = jest.spyOn(containerTemplateServiceMock, "postTemplateEdits");
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    const navigateSpy = jest.spyOn(router, "navigateByUrl");

    fillValid();
    jest.spyOn(editComponent(), "collectTokens").mockReturnValue(null);
    const scrollSpy = jest.spyOn(editComponent(), "scrollToFirstInvalid");
    await component.onAction("save");

    expect(notificationService.warning).toHaveBeenCalledWith("There are invalid token configurations.");
    expect(scrollSpy).toHaveBeenCalled();
    expect(postSpy).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("navigates back when onCancel dialog returns 'discard'", () => {
    component.template.update((t) => ({ ...t, name: "Changed" }));
    expect(component.isDirty()).toBe(true);

    const dialogService = TestBed.inject(DialogService);
    const openDialogSpy = jest.spyOn(dialogService, "openDialog");
    const navigateSpy = jest.spyOn(router, "navigateByUrl");
    const clearSpy = jest.spyOn(TestBed.inject(PendingChangesService), "clearAllRegistrations");

    component.onCancel();
    const dialogRef = openDialogSpy.mock.results[0].value;
    dialogRef.close("discard");

    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    expect(clearSpy).toHaveBeenCalled();
  });

  it("should not call deleteTemplate when save fails even if template was renamed", async () => {
    const oldData = { name: "OldName", container_type: "type1", template_options: { tokens: [] }, default: false };
    component.initTemplate.set(oldData);
    fillValid();
    component.template.update((t) => ({ ...t, name: "NewName" }));

    jest.spyOn(containerTemplateServiceMock, "postTemplateEdits").mockResolvedValue(false);
    const deleteSpy = jest.spyOn(containerTemplateServiceMock, "deleteTemplate");

    await component.onAction("save");

    expect(deleteSpy).not.toHaveBeenCalled();
  });

  describe("deleteTemplate", () => {
    const existing: ContainerTemplate = {
      name: "ToDelete",
      container_type: "generic",
      template_options: { tokens: [] },
      default: false
    };
    let dialogService: MockDialogService;
    let pendingChangesService: MockPendingChangesService;

    beforeEach(() => {
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      component.initTemplate.set(existing);
    });

    it("does nothing without a loaded template", async () => {
      component.initTemplate.set(null);
      await component.deleteTemplate();
      expect(dialogService.openDialogAsync).not.toHaveBeenCalled();
      expect(containerTemplateServiceMock.deleteTemplate).not.toHaveBeenCalled();
    });

    it("does not delete when the dialog is not confirmed", async () => {
      dialogService.openDialogAsync.mockResolvedValue(false);
      await component.deleteTemplate();
      expect(dialogService.openDialogAsync).toHaveBeenCalledWith(
        expect.objectContaining({ component: ContainerTemplateDeleteDialogComponent, data: [existing] })
      );
      expect(containerTemplateServiceMock.deleteTemplate).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("deletes the template and navigates back after confirmation", async () => {
      await component.deleteTemplate();
      expect(containerTemplateServiceMock.deleteTemplate).toHaveBeenCalledWith("ToDelete");
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    });

    it("stays on the page when the deletion fails", async () => {
      containerTemplateServiceMock.deleteTemplate.mockRejectedValue(new Error("delete failed"));
      await component.deleteTemplate();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });
});

describe("ContainerTemplateEditPageComponent on a details deep link", () => {
  const stored: ContainerTemplate = {
    name: "Stored",
    container_type: "generic",
    template_options: { tokens: [] },
    default: false
  };
  let fixture: ComponentFixture<ContainerTemplateEditPageComponent>;
  let component: ContainerTemplateEditPageComponent;
  let templatesService: MockContainerTemplateService;
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let warn: jest.SpyInstance;

  const loadingState = (loading: boolean) =>
    (templatesService.templatesResource as unknown as { isLoading: { set(v: boolean): void } }).isLoading.set(loading);
  const editComponents = () => fixture.debugElement.queryAll(By.directive(ContainerTemplateEditComponent));

  beforeEach(async () => {
    paramMap$ = new BehaviorSubject(convertToParamMap({ name: "Stored" }));
    warn = jest.spyOn(console, "warn").mockImplementation(() => undefined);
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } },
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } }
      ]
    }).compileComponents();
    templatesService = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    loadingState(true);
    fixture = TestBed.createComponent(ContainerTemplateEditPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => warn.mockRestore());

  it("waits for the templates before it shows the form and does not warn", () => {
    expect(editComponents().length).toBe(0);
    expect(component.isNewTemplate()).toBe(true);
    expect(warn).not.toHaveBeenCalled();
  });

  it("opens the template once the templates are loaded", () => {
    templatesService.templates.set([stored]);
    loadingState(false);
    fixture.detectChanges();

    expect(component.initTemplate()).toEqual(stored);
    expect(component.isNewTemplate()).toBe(false);
    expect(component.template().name).toBe("Stored");
    expect(editComponents().length).toBe(1);
    expect(warn).not.toHaveBeenCalled();
  });

  it("keeps the edits of the user when the templates are reloaded", () => {
    templatesService.templates.set([stored]);
    loadingState(false);
    fixture.detectChanges();
    component.template.update((t) => ({ ...t, container_type: "smartphone" }));

    templatesService.templates.set([{ ...stored }]);
    fixture.detectChanges();

    expect(component.template().container_type).toBe("smartphone");
  });

  it("warns and shows an empty form when the loaded templates do not have the name", () => {
    templatesService.templates.set([{ ...stored, name: "Other" }]);
    loadingState(false);
    fixture.detectChanges();

    expect(component.initTemplate()).toBeNull();
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("No template found"), "Stored");
    expect(editComponents().length).toBe(1);
  });

  it("clears the template when the route has no name any more", () => {
    templatesService.templates.set([stored]);
    loadingState(false);
    fixture.detectChanges();

    paramMap$.next(convertToParamMap({}));
    fixture.detectChanges();

    expect(component.initTemplate()).toBeNull();
    expect(editComponents().length).toBe(1);
  });
});

describe("ContainerTemplateEditPageComponent on a details deep link with the real template service", () => {
  it("opens a template of any container type once the list is loaded", async () => {
    TestBed.configureTestingModule({
      imports: [ContainerTemplateEditPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ContainerTemplateService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ name: "Phone" })) } }
      ]
    });
    (TestBed.inject(AuthService) as unknown as MockAuthService).actionAllowed.mockReturnValue(true);
    (TestBed.inject(ContentService) as unknown as MockContentService).routeUrl.set(
      ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS + "Phone"
    );
    (TestBed.inject(ContainerService) as unknown as MockContainerService).selectedContainerType.set({
      containerType: "generic",
      description: "",
      token_types: []
    });
    const warn = jest.spyOn(console, "warn").mockImplementation(() => undefined);
    const httpMock = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ContainerTemplateEditPageComponent);
    fixture.detectChanges();

    expect(fixture.debugElement.queryAll(By.directive(ContainerTemplateEditComponent)).length).toBe(0);

    const list = httpMock.expectOne((req) => req.url.endsWith("/container/templates"));
    expect(list.request.params.has("container_type")).toBe(false);
    list.flush({
      result: {
        value: {
          templates: [{ name: "Phone", container_type: "smartphone", template_options: { tokens: [] }, default: false }]
        }
      }
    });
    httpMock
      .match((req) => req.url.endsWith("/container/template/tokentypes"))
      .forEach((req) => req.flush({ result: { value: {} } }));
    TestBed.tick();
    await Promise.resolve();
    fixture.detectChanges();

    expect(fixture.componentInstance.initTemplate()?.name).toBe("Phone");
    expect(fixture.componentInstance.template().container_type).toBe("smartphone");
    expect(fixture.debugElement.queryAll(By.directive(ContainerTemplateEditComponent)).length).toBe(1);
    expect(warn).not.toHaveBeenCalled();
    warn.mockRestore();
  });
});
