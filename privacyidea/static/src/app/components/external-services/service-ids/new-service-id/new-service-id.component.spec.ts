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
import { MatDialogRef } from "@angular/material/dialog";
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import {
  SaveAndExitDialogComponent,
  SaveAndExitDialogResult
} from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { ServiceIdService } from "@services/service-id/service-id.service";
import { MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockServiceIdService } from "@testing/mock-services/mock-service-id-service";
import { of } from "rxjs";
import { NewServiceIdComponent } from "./new-service-id.component";

describe("NewServiceIdComponent", () => {
  let component: NewServiceIdComponent;
  let fixture: ComponentFixture<NewServiceIdComponent>;
  let serviceIdServiceMock: MockServiceIdService;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewServiceIdComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({})) }
        },
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    serviceIdServiceMock = TestBed.inject(ServiceIdService) as unknown as MockServiceIdService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    fixture = TestBed.createComponent(NewServiceIdComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode()).toBe(false);
    expect(component.serviceIdModel().servicename).toBe("");
  });

  it("should call save when form is valid", async () => {
    component.serviceIdModel.update((m) => ({
      ...m,
      servicename: "test",
      description: "desc"
    }));

    const success = await component.save();

    expect(success).toBe(true);
    expect(serviceIdServiceMock.postServiceId).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
  });

  it("should keep on page if save fails", async () => {
    component.serviceIdModel.update((m) => ({
      ...m,
      servicename: "test",
      description: "desc"
    }));
    serviceIdServiceMock.postServiceId = jest.fn().mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(serviceIdServiceMock.postServiceId).toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it("posts the name and the description exactly as typed, a blank description included", async () => {
    component.serviceIdModel.set({ servicename: "test", description: "   " });

    await component.save();

    expect(serviceIdServiceMock.postServiceId).toHaveBeenCalledWith({ servicename: "test", description: "   " });
  });

  describe("identifier field", () => {
    const identifierInput = () => fixture.nativeElement.querySelector("input") as HTMLInputElement;
    const type = async (value: string) => {
      identifierInput().value = value;
      identifierInput().dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    it("reports required, then the invalid characters, once the field is touched", async () => {
      await type("bad name");
      expect(
        component.serviceIdForm
          .servicename()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["pattern"]);
      identifierInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(fixture.nativeElement.textContent).toContain("invalid characters");

      await type("");
      identifierInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(
        component.serviceIdForm
          .servicename()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
      expect(fixture.nativeElement.textContent).toContain("is required");
    });

    it("marks the form dirty when the clear button empties the field", async () => {
      await type("name");
      component.serviceIdForm().reset();
      expect(component.hasChanges).toBe(false);
      const clear = identifierInput().closest("app-clearable-input")!.querySelector("button") as HTMLButtonElement;
      clear.click();
      fixture.detectChanges();
      expect(component.serviceIdModel().servicename).toBe("");
      expect(component.hasChanges).toBe(true);
    });
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: Partial<MatDialogRef<SaveAndExitDialogComponent, SaveAndExitDialogResult>> & {
      afterClosed: jest.Mock;
    };

    beforeEach(() => {
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
    });

    it("should navigate back directly when there are no changes", () => {
      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.serviceIdModel.update((m) => ({
        ...m,
        servicename: "test",
        description: "desc"
      }));
      component.serviceIdForm().markAsDirty();

      component.onCancel();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: SaveAndExitDialogComponent,
          data: expect.objectContaining({
            allowSaveExit: true
          })
        })
      );
    });

    it("should navigate back when user selects 'discard' in cancel dialog", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.serviceIdModel.update((m) => ({
        ...m,
        servicename: "test",
        description: "desc"
      }));
      component.serviceIdForm().markAsDirty();

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    });

    it("should navigate back when user selects 'save-exit' and save succeeds", async () => {
      component.serviceIdModel.update((m) => ({
        ...m,
        servicename: "test",
        description: "desc"
      }));
      component.serviceIdForm().markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    });

    it("should NOT navigate back when user selects 'save-exit' but save fails", async () => {
      component.serviceIdModel.update((m) => ({
        ...m,
        servicename: "test",
        description: "desc"
      }));
      component.serviceIdForm().markAsDirty();
      serviceIdServiceMock.postServiceId = jest.fn().mockRejectedValue(new Error("Save failed"));
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      component.serviceIdModel.update((m) => ({ ...m, servicename: "" }));
      component.serviceIdForm().markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.save).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user closes dialog without selecting an option", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.serviceIdModel.update((m) => ({
        ...m,
        servicename: "test",
        description: "desc"
      }));
      component.serviceIdForm().markAsDirty();

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });

  describe("deleteServiceId", () => {
    let dialog: MockDialogService;
    let pending: MockPendingChangesService;
    let service: MockServiceIdService;
    let navigateSpy: jest.SpyInstance;

    beforeEach(() => {
      dialog = TestBed.inject(DialogService) as unknown as MockDialogService;
      pending = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      service = TestBed.inject(ServiceIdService) as unknown as MockServiceIdService;
      navigateSpy = jest.spyOn(TestBed.inject(Router), "navigateByUrl").mockResolvedValue(true);
      component["editServiceName"] = "service-id";
    });

    it("does nothing without an identifier", async () => {
      component["editServiceName"] = null;
      await component.deleteServiceId();
      expect(dialog.confirmDelete).not.toHaveBeenCalled();
      expect(service.deleteServiceId).not.toHaveBeenCalled();
    });

    it("does not delete when the confirmation is cancelled", async () => {
      dialog.confirmDelete.mockResolvedValue(false);
      await component.deleteServiceId();
      expect(service.deleteServiceId).not.toHaveBeenCalled();
      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("deletes after confirmation and navigates back to the list", async () => {
      await component.deleteServiceId();
      expect(dialog.confirmDelete).toHaveBeenCalledWith(expect.objectContaining({ items: ["service-id"] }));
      expect(service.deleteServiceId).toHaveBeenCalledWith("service-id");
      expect(pending.clearAllRegistrations).toHaveBeenCalled();
      expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    });

    it("stays on the page when the deletion fails", async () => {
      service.deleteServiceId.mockRejectedValue(new Error("delete failed"));
      await component.deleteServiceId();
      expect(pending.clearAllRegistrations).not.toHaveBeenCalled();
      expect(navigateSpy).not.toHaveBeenCalled();
    });
  });
});

describe("NewServiceIdComponent edit mode", () => {
  let component: NewServiceIdComponent;
  let fixture: ComponentFixture<NewServiceIdComponent>;
  let serviceIdServiceMock: MockServiceIdService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewServiceIdComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({ name: "existing-service" })) }
        },
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    serviceIdServiceMock = TestBed.inject(ServiceIdService) as unknown as MockServiceIdService;
    serviceIdServiceMock.serviceIds.set([{ servicename: "existing-service", description: "existing" }]);
    jest.spyOn(TestBed.inject(Router), "navigateByUrl").mockResolvedValue(true);

    fixture = TestBed.createComponent(NewServiceIdComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("loads the service ID and disables its name", () => {
    expect(component.isEditMode()).toBe(true);
    expect(component.serviceIdModel()).toEqual({ servicename: "existing-service", description: "existing" });
    expect(component.serviceIdForm.servicename().disabled()).toBe(true);
    const nameInput = fixture.nativeElement.querySelector("app-clearable-input input") as HTMLInputElement;
    expect(nameInput.disabled).toBe(true);
  });
});
