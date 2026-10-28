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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { ResolverService, ResolverType } from "@services/resolver/resolver.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockDialogService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { of, throwError } from "rxjs";
import { UserNewResolverComponent } from "./user-new-resolver.component";

interface MockResolverResourceShape {
  value: WritableSignal<unknown>;
  status: WritableSignal<string>;
  hasValue: jest.Mock<boolean>;
}

(globalThis as {
  IntersectionObserver: typeof IntersectionObserver
}).IntersectionObserver = class IntersectionObserver {
  disconnect = jest.fn();
  observe = jest.fn();
  unobserve = jest.fn();
  takeRecords = jest.fn().mockReturnValue([]);
} as unknown as typeof IntersectionObserver;

describe("UserNewResolverComponent", () => {
  let component: UserNewResolverComponent;
  let fixture: ComponentFixture<UserNewResolverComponent>;
  let resolverService: MockResolverService;
  let dialogService: MockDialogService;
  let mockSaveExitDialogRef: MockMatDialogRef<SaveAndExitDialogComponent>;
  let pendingChangesService: MockPendingChangesService;
  let router: Router;

  function setResolverType(type: ResolverType) {
    component.resolverSettingsModel.update((m) => ({ ...m, resolverType: type }));
  }

  async function detectChangesStable() {
    fixture.detectChanges(false);
    await fixture.whenStable();
    fixture.detectChanges(false);
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserNewResolverComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: () => "" })
          }
        },
        {
          provide: Router,
          useValue: {
            navigate: jest.fn(),
            navigateByUrl: jest.fn(),
            events: of(),
            url: ROUTE_PATHS.USERS_RESOLVERS
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserNewResolverComponent);
    component = fixture.componentInstance;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    router = TestBed.inject(Router);

    // Create a reusable mock dialog ref for SaveAndExitDialog
    mockSaveExitDialogRef = new MockMatDialogRef();
  });

  it("should create", async () => {
    await detectChangesStable();
    expect(component).toBeTruthy();
  });

  it("should pre-fill form when a resolver is selected (edit mode)", async () => {
    const resolverName = "test-resolver";
    const resolverData = {
      [resolverName]: {
        resolvername: resolverName,
        type: "passwdresolver",
        censor_keys: [],
        data: {
          fileName: "/tmp/test"
        }
      }
    };

    resolverService.selectedResolverName.set(resolverName);

    const resourceValue = signal({
      result: {
        status: true,
        value: resolverData
      }
    });
    const resourceStatus = signal("resolved");

    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).value = resourceValue;
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).status = resourceStatus;
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).hasValue = jest
      .fn()
      .mockReturnValue(true);

    await detectChangesStable();

    expect(component.isEditMode()).toBeTruthy();
    expect(component.resolverNameModel().resolverName).toBe(resolverName);
    expect(component.resolverType()).toBe("passwdresolver");
    expect(component.formData["fileName"]).toBe("/tmp/test");

    const inputElement = fixture.nativeElement.querySelector("input[placeholder=\"/etc/passwd\"]");
    expect(inputElement?.value).toBe("/tmp/test");
  });

  it("should pre-fill form for sqlresolver when selected (edit mode)", async () => {
    const resolverName = "sql-res";
    const resolverData = {
      [resolverName]: {
        resolvername: resolverName,
        type: "sqlresolver",
        censor_keys: [],
        data: {
          Database: "testdb",
          Driver: "mysql"
        }
      }
    };

    resolverService.selectedResolverName.set(resolverName);

    const resourceValue = signal({
      result: {
        status: true,
        value: resolverData
      }
    });
    const resourceStatus = signal("resolved");

    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).value = resourceValue;
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).status = resourceStatus;
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).hasValue = jest
      .fn()
      .mockReturnValue(true);

    await detectChangesStable();

    expect(component.isEditMode()).toBeTruthy();
    expect(component.resolverType()).toBe("sqlresolver");

    const dbInput = fixture.nativeElement.querySelector("input[placeholder=\"YourDatabase\"]");
    expect(dbInput?.value).toBe("testdb");
  });

  it("should re-fill form when resource reloads", async () => {
    const resolverName = "test-resolver";
    const initialData = {
      [resolverName]: {
        resolvername: resolverName,
        type: "passwdresolver",
        censor_keys: [],
        data: { fileName: "/initial" }
      }
    };

    resolverService.selectedResolverName.set(resolverName);

    const resourceValue = signal({
      result: { status: true, value: initialData }
    });
    const resourceStatus = signal("resolved");

    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).value = resourceValue;
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).status = resourceStatus;
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).hasValue = jest
      .fn()
      .mockReturnValue(true);

    await detectChangesStable();
    expect(component.formData["fileName"]).toBe("/initial");

    resourceStatus.set("reloading");
    await detectChangesStable();

    const updatedData = {
      [resolverName]: {
        resolvername: resolverName,
        type: "passwdresolver",
        censor_keys: [],
        data: { fileName: "/updated" }
      }
    };

    resourceValue.set({ result: { status: true, value: updatedData } });
    resourceStatus.set("resolved");

    await detectChangesStable();
    expect(component.formData["fileName"]).toBe("/updated");
  });

  it("should show error and not redirect when postResolver returns status true but value -1", async () => {
    await detectChangesStable();

    const resolverName = "test-error";
    component.resolverNameModel.set({ resolverName });
    setResolverType("sqlresolver");

    const errorResponse = new MockPiResponse<number, { description: string }>({
      result: {
        status: true,
        value: -1
      },
      detail: {
        description: "Unable to connect to database."
      }
    });

    resolverService.postResolver.mockReturnValue(of(errorResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onSave();

    expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("Unable to connect to database."));
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(component.resolverNameModel().resolverName).toBe(resolverName);
  });

  it("should show error when postResolverTest returns status true but value -1", async () => {
    await detectChangesStable();

    setResolverType("sqlresolver");

    const errorResponse = new MockPiResponse<boolean, { description: string }>({
      result: {
        status: true,
        value: false
      },
      detail: {
        description: "Connection test failed."
      }
    });

    resolverService.postResolverTest.mockReturnValue(of(errorResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();

    expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("Connection test failed."));
  });

  it("should show success on save and navigate to resolvers list", async () => {
    await detectChangesStable();
    component.resolverNameModel.set({ resolverName: "new-res" });
    setResolverType("passwdresolver");

    const successResponse = new MockPiResponse<number>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolver.mockReturnValue(of(successResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    const success = await component.onSave();

    expect(success).toBe(true);
    expect(notificationService.success).toHaveBeenCalledWith(expect.stringContaining("created"));
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
  });

  it("should show success on save in edit mode and navigate to resolvers list", async () => {
    resolverService.selectedResolverName.set("edit-res");
    const resolverData = {
      "edit-res": {
        resolvername: "edit-res",
        type: "passwdresolver",
        censor_keys: [],
        data: { fileName: "/etc/passwd" }
      }
    };
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).value.set({
      result: { status: true, value: resolverData }
    });
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).hasValue = jest
      .fn()
      .mockReturnValue(true);
    await detectChangesStable();

    const successResponse = new MockPiResponse<number>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolver.mockReturnValue(of(successResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    const success = await component.onSave();

    expect(success).toBe(true);
    expect(notificationService.success).toHaveBeenCalledWith(expect.stringContaining("updated"));
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
  });

  it("should show error on save when subscription fails", async () => {
    component.resolverNameModel.set({ resolverName: "err-res" });
    setResolverType("passwdresolver");
    fixture.detectChanges();

    const errorResponse = {
      message: "Network error",
      error: { result: { error: { message: "Detailed error" } } }
    };
    resolverService.postResolver.mockReturnValue(throwError(() => errorResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    const success = await component.onSave();

    expect(success).toBe(false);
    expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("Detailed error"));
  });

  it("should validate before save", async () => {
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.resolverNameModel.set({ resolverName: "" });
    let success = await component.onSave();
    expect(success).toBe(false);
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("enter a resolver name"));

    component.resolverNameModel.set({ resolverName: "res" });
    setResolverType("" as unknown as ResolverType);
    success = await component.onSave();
    expect(success).toBe(false);
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    setResolverType("passwdresolver");
    await detectChangesStable();
    component.passwdResolver()?.model.set({ fileName: "" });
    success = await component.onSave();
    expect(success).toBe(false);
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("fill in all required fields"));
  });

  it.each(["test", ".", ".."])("rejects the reserved name %p", (name) => {
    setResolverType("passwdresolver");
    component.resolverNameModel.set({ resolverName: name });
    expect(component.resolverNameForm.resolverName().errors().some((e) => e.kind === "reservedName")).toBe(true);
    expect(component.canSave).toBe(false);
  });

  it("should include additional fields in save payload", async () => {
    component.resolverNameModel.set({ resolverName: "res" });
    setResolverType("passwdresolver");
    await detectChangesStable();
    component.passwdResolver()?.model.set({ fileName: "/etc/passwd" });

    resolverService.postResolver.mockReturnValue(of(new MockPiResponse({ result: { status: true, value: 1 } })));
    component.onSave();

    expect(resolverService.postResolver).toHaveBeenCalledWith(
      "res",
      expect.objectContaining({
        fileName: "/etc/passwd"
      })
    );
  });

  it("should execute test successfully", async () => {
    setResolverType("passwdresolver");
    fixture.detectChanges();
    const successResponse = MockPiResponse.fromValue<boolean, { description: string }>(true, { description: "ok" });
    resolverService.postResolverTest.mockReturnValue(of(successResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();
    expect(notificationService.success).toHaveBeenCalledWith(expect.stringContaining("Resolver test executed:"), {
      duration: 20000
    });

    component.onQuickTest();
    expect(notificationService.success).toHaveBeenCalledWith(expect.stringContaining("Resolver test executed:"), {
      duration: 20000
    });
  });

  it("should show error on test when subscription fails", async () => {
    setResolverType("passwdresolver");
    fixture.detectChanges();

    const errorResponse = { message: "Network error" };

    resolverService.postResolverTest.mockReturnValue(throwError(() => errorResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();

    expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("should validate before test", async () => {
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    setResolverType("" as unknown as ResolverType);
    component.onTest();
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    setResolverType("passwdresolver");
    await detectChangesStable();
    component.passwdResolver()?.model.set({ fileName: "" });
    component.onTest();
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("fill in all required fields"));
  });

  it("should include resolver name in test payload when in edit mode", async () => {
    resolverService.selectedResolverName.set("edit-res");
    const resolverData = {
      "edit-res": {
        resolvername: "edit-res",
        type: "passwdresolver",
        censor_keys: [],
        data: { fileName: "/etc/passwd" }
      }
    };
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).value.set({
      result: { status: true, value: resolverData }
    });
    (resolverService.selectedResolverResource as unknown as MockResolverResourceShape).hasValue = jest
      .fn()
      .mockReturnValue(true);
    await detectChangesStable();

    resolverService.postResolverTest.mockReturnValue(
      of(new MockPiResponse<boolean, { description: string }>({ result: { status: true, value: true } }))
    );
    component.onTest();

    expect(resolverService.postResolverTest).toHaveBeenCalledWith(
      expect.objectContaining({
        resolver: "edit-res"
      })
    );
  });

  it("should handle type change", () => {
    const changeType = (type: ResolverType) => {
      setResolverType(type);
      component.onTypeChange(type);
    };

    changeType("sqlresolver");
    expect(component.resolverType()).toBe("sqlresolver");

    changeType("ldapresolver");
    expect(component.resolverType()).toBe("ldapresolver");
    expect(component.formData["TLS_VERSION"]).toBe("2");

    changeType("entraidresolver");
    expect(component.formData).toEqual({});

    changeType("keycloakresolver");
    expect(component.formData).toEqual({});

    changeType("httpresolver");
    expect(component.formData["responseMapping"]).toBeUndefined();

    changeType("passwdresolver");
    expect(component.formData["fileName"]).toBe("/etc/passwd");
  });

  it("should open SaveAndExitDialogComponent on cancel when there are changes", async () => {
    mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
    dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);

    component.resolverNameModel.set({ resolverName: "changed" });
    await detectChangesStable();

    component.onCancel();

    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        component: SaveAndExitDialogComponent
      })
    );
  });

  it("should navigate to resolvers list directly when there are no changes", async () => {
    await detectChangesStable();

    component.onCancel();

    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
  });

  it("should navigate to resolvers list when user selects 'discard' in cancel dialog", async () => {
    mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
    dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);

    component.resolverNameModel.set({ resolverName: "changed" });
    await detectChangesStable();

    component.onCancel();

    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
  });

  it("should navigate to resolvers list when user selects 'save-exit' and save succeeds", async () => {
    component.resolverNameModel.set({ resolverName: "test-res" });
    setResolverType("passwdresolver");
    await detectChangesStable();

    mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
    dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);

    const successResponse = new MockPiResponse<number>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolver.mockReturnValue(of(successResponse));
    pendingChangesService.save.mockReturnValue(Promise.resolve(true));

    component.onCancel();

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
  });

  it("should NOT navigate when user selects 'save-exit' but save fails", async () => {
    component.resolverNameModel.set({ resolverName: "test-res" });
    setResolverType("passwdresolver");
    await detectChangesStable();

    mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
    dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);

    const errorResponse = new MockPiResponse<number>({
      result: { status: true, value: -1 },
      detail: { description: "Save failed" }
    });
    resolverService.postResolver.mockReturnValue(of(errorResponse));
    pendingChangesService.save.mockReturnValue(Promise.resolve(false));

    jest.mocked(router.navigateByUrl).mockClear();

    component.onCancel();

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
    component.resolverNameModel.set({ resolverName: "" });
    await detectChangesStable();

    mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
    dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);

    component.resolverSettingsModel.update((m) => ({ ...m, testUsername: "test" }));
    await detectChangesStable();

    component.onCancel();

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(pendingChangesService.save).not.toHaveBeenCalled();
    expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should do nothing when user closes dialog without selecting an option", async () => {
    mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
    dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);

    component.resolverNameModel.set({ resolverName: "changed" });
    await detectChangesStable();

    component.onCancel();

    expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  describe("deleteResolver", () => {
    let notificationService: MockNotificationService;

    beforeEach(() => {
      notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
      resolverService.selectedResolverName.set("ldap1");
    });

    it("does nothing without a selected resolver", async () => {
      resolverService.selectedResolverName.set("");
      await component.deleteResolver();
      expect(dialogService.confirmDelete).not.toHaveBeenCalled();
      expect(resolverService.deleteResolver).not.toHaveBeenCalled();
    });

    it("does not delete when the confirmation is cancelled", async () => {
      dialogService.confirmDelete.mockResolvedValue(false);
      await component.deleteResolver();
      expect(resolverService.deleteResolver).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("deletes the resolver, reloads the list and navigates back", async () => {
      await component.deleteResolver();
      expect(dialogService.confirmDelete).toHaveBeenCalledWith(expect.objectContaining({ items: ["ldap1"] }));
      expect(resolverService.deleteResolver).toHaveBeenCalledWith("ldap1");
      expect(notificationService.success).toHaveBeenCalledWith(expect.stringContaining("ldap1"));
      expect(resolverService.resolversResource.reload).toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
    });

    it.each([
      ["a negative result", new MockPiResponse<number>({ result: { status: true, value: -1 } })],
      ["a failed status", new MockPiResponse<number>({ result: { status: false, value: 1 } })],
      ["a missing value", new MockPiResponse<number>({ result: { status: true, value: undefined } })]
    ])("reports the resolver as not found on %s", async (_label, response) => {
      resolverService.deleteResolver.mockReturnValue(of(response));
      await component.deleteResolver();
      expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("ldap1"));
      expect(notificationService.success).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("reports the server message when the deletion is rejected", async () => {
      resolverService.deleteResolver.mockReturnValue(
        throwError(() => ({ error: { result: { error: { message: "resolver is in use" } } } }))
      );
      await component.deleteResolver();
      expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("resolver is in use"));
      expect(notificationService.success).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });

  describe("form controls", () => {
    const loadResolver = async (name: string, type: ResolverType, data: Record<string, unknown>) => {
      resolverService.selectedResolverName.set(name);
      const resource = resolverService.selectedResolverResource as unknown as MockResolverResourceShape;
      resource.value = signal({
        result: { status: true, value: { [name]: { resolvername: name, type, censor_keys: [], data } } }
      });
      resource.status = signal("resolved");
      resource.hasValue = jest.fn().mockReturnValue(true);
      await detectChangesStable();
    };
    const typeSelect = (): MatSelect =>
      fixture.debugElement.query(By.css(".resolver-type-select mat-select")).injector.get(MatSelect);
    const inputByLabel = (label: string): HTMLInputElement =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-form-field") as NodeListOf<HTMLElement>)
        .find((el) => el.querySelector("mat-label")?.textContent?.includes(label))!
        .querySelector("input") as HTMLInputElement;
    const checkboxInput = (label: string): HTMLInputElement =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-checkbox") as NodeListOf<HTMLElement>)
        .find((el) => el.textContent?.includes(label))!
        .querySelector("input") as HTMLInputElement;
    const clearButtonOf = (input: HTMLInputElement) =>
      input.closest("app-clearable-input")!.querySelector("button") as HTMLButtonElement;
    const type = async (input: HTMLInputElement, value: string) => {
      input.value = value;
      input.dispatchEvent(new Event("input"));
      input.dispatchEvent(new Event("blur"));
      await detectChangesStable();
    };

    beforeEach(() => {
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
    });

    describe("resolver type select", () => {
      it("starts with the passwd type and a pristine form", async () => {
        await detectChangesStable();

        expect(typeSelect().value).toBe("passwdresolver");
        expect(component.resolverSettingsForm().dirty()).toBe(false);
        expect(component.hasChanges).toBe(false);
      });

      it("writes the chosen type to the form, resets the form data and shows the matching editor", async () => {
        await detectChangesStable();

        typeSelect()
          .options.find((o) => o.value === "ldapresolver")!
          .select();
        await detectChangesStable();

        expect(component.resolverType()).toBe("ldapresolver");
        expect(component.resolverSettingsForm.resolverType().dirty()).toBe(true);
        expect(component.formData["TLS_VERSION"]).toBe("2");
        expect(fixture.nativeElement.querySelector("app-ldap-resolver")).not.toBeNull();
        expect(fixture.nativeElement.querySelector("app-passwd-resolver")).toBeNull();
      });

      it("reflects a type set on the model in the select", async () => {
        setResolverType("sqlresolver");
        await detectChangesStable();

        expect(typeSelect().value).toBe("sqlresolver");
      });

      it("is disabled in edit mode and keeps showing the type of the loaded resolver", async () => {
        await loadResolver("sql-res", "sqlresolver", { Driver: "mysql" });

        expect(component.resolverSettingsForm.resolverType().disabled()).toBe(true);
        expect(typeSelect().disabled).toBe(true);
        expect(typeSelect().value).toBe("sqlresolver");
        expect(typeSelect().triggerValue).toBe("SQL");
      });

      it("ignores a type change in edit mode", async () => {
        await loadResolver("sql-res", "sqlresolver", { Driver: "mysql" });

        component.onTypeChange("ldapresolver");

        expect(component.formData).toEqual({ Driver: "mysql" });
      });

      it("is enabled again for a new resolver after leaving edit mode", async () => {
        await loadResolver("sql-res", "sqlresolver", { Driver: "mysql" });

        resolverService.selectedResolverName.set("");
        await detectChangesStable();

        expect(component.resolverSettingsForm.resolverType().disabled()).toBe(false);
        expect(component.resolverType()).toBe("passwdresolver");
        expect(component.resolverSettingsForm().dirty()).toBe(false);
      });
    });

    describe("test user inputs", () => {
      beforeEach(async () => {
        setResolverType("httpresolver");
        await detectChangesStable();
      });

      it("are shown for the http resolver and hidden for the passwd resolver", async () => {
        expect(inputByLabel("Test Username")).toBeTruthy();
        expect(inputByLabel("Test User ID")).toBeTruthy();

        setResolverType("passwdresolver");
        await detectChangesStable();

        expect(fixture.nativeElement.textContent).not.toContain("Test Username");
      });

      it("write the typed values to the form and mark it dirty", async () => {
        await type(inputByLabel("Test Username"), "alice");
        await type(inputByLabel("Test User ID"), "1001");

        expect(component.testUsername()).toBe("alice");
        expect(component.testUserId()).toBe("1001");
        expect(component.resolverSettingsForm.testUsername().dirty()).toBe(true);
        expect(component.resolverSettingsForm.testUserId().dirty()).toBe(true);
      });

      it("show a value set on the model", async () => {
        component.resolverSettingsModel.update((m) => ({ ...m, testUsername: "bob" }));
        await detectChangesStable();

        expect(inputByLabel("Test Username").value).toBe("bob");
      });

      it("empty through the clear buttons and mark the form dirty", async () => {
        component.resolverSettingsModel.update((m) => ({ ...m, testUsername: "bob", testUserId: "7" }));
        await detectChangesStable();

        clearButtonOf(inputByLabel("Test Username")).click();
        clearButtonOf(inputByLabel("Test User ID")).click();
        await detectChangesStable();

        expect(component.testUsername()).toBe("");
        expect(component.testUserId()).toBe("");
        expect(component.resolverSettingsForm.testUsername().dirty()).toBe(true);
        expect(component.resolverSettingsForm.testUserId().dirty()).toBe(true);
      });

      it("are sent with a connection test", async () => {
        await type(inputByLabel("Test Username"), "alice");
        await type(inputByLabel("Test User ID"), "1001");
        jest.spyOn(component, "isAdditionalFieldsInvalid", "get").mockReturnValue(false);

        component.onTest();

        expect(resolverService.postResolverTest).toHaveBeenCalledWith(
          expect.objectContaining({ type: "httpresolver", test_username: "alice", test_userid: "1001" })
        );
      });
    });

    describe("resolver name", () => {
      const nameInput = () => fixture.nativeElement.querySelector("input[placeholder='resolver1']") as HTMLInputElement;
      const errors = () =>
        Array.from(fixture.nativeElement.querySelectorAll("mat-error") as NodeListOf<HTMLElement>).map(
          (e) => e.textContent
        );

      beforeEach(() => detectChangesStable());

      it("shows the required message once the emptied name is touched", async () => {
        await type(nameInput(), "x");
        await type(nameInput(), "");

        expect(errors().join(" ")).toContain("required");
      });

      it("shows the invalid characters message", async () => {
        await type(nameInput(), "a b");

        expect(errors().join(" ")).toContain("invalid characters");
      });

      it("shows the reserved name message", async () => {
        await type(nameInput(), "test");

        expect(errors().join(" ")).toContain("Cannot be named");
      });

      it("marks the name dirty when the clear button empties it", async () => {
        await type(nameInput(), "abc");
        component.resolverNameForm().reset();
        await detectChangesStable();

        clearButtonOf(nameInput()).click();
        await detectChangesStable();

        expect(component.resolverName).toBe("");
        expect(component.resolverNameForm.resolverName().dirty()).toBe(true);
      });
    });

    describe("cancel guard for edits that only toggle a checkbox, select or clear button", () => {
      const ldapData = {
        LDAPURI: "ldap://ldap.example.com",
        LDAPBASE: "dc=example,dc=com",
        LOGINNAMEATTRIBUTE: "uid",
        LDAPSEARCHFILTER: "(uid=*)",
        USERINFO: "{}",
        START_TLS: true,
        TLS_VERIFY: true
      };

      it("does not warn for a loaded resolver that was not edited", async () => {
        await loadResolver("ldap1", "ldapresolver", ldapData);

        expect(component.hasChanges).toBe(false);
        component.onCancel();

        expect(dialogService.openDialog).not.toHaveBeenCalled();
        expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS);
      });

      it.each([
        ["STARTTLS"],
        ["Verify TLS certificate"],
        ["Per-Process Server Pool"],
        ["Edit User Store"],
        ["Recursive Search of User Groups"],
        ["No Anonymous Referral Chasing"],
        ["No Retrieval of Schema Information"]
      ])("an LDAP checkbox %s trips the guard", async (label) => {
        await loadResolver("ldap1", "ldapresolver", ldapData);

        checkboxInput(label).click();
        await detectChangesStable();

        expect(component.ldapResolver()!.isDirty()).toBe(true);
        expect(component.hasChanges).toBe(true);
        component.onCancel();
        expect(dialogService.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({ component: SaveAndExitDialogComponent })
        );
        expect(router.navigateByUrl).not.toHaveBeenCalled();
      });

      it.each([
        ["Scope", "BASE"],
        ["TLS Version", "5"],
        ["Bind Type", "Anonymous"]
      ])("the LDAP %s select trips the guard", async (label, value) => {
        await loadResolver("ldap1", "ldapresolver", ldapData);

        const select = fixture.debugElement
          .queryAll(By.directive(MatSelect))
          .find((d) => d.nativeElement.closest("mat-form-field")?.textContent?.includes(label))!
          .injector.get(MatSelect);
        select.options.find((o) => o.value === value)!.select();
        await detectChangesStable();

        expect(component.hasChanges).toBe(true);
        component.onCancel();
        expect(dialogService.openDialog).toHaveBeenCalled();
      });

      it("an LDAP clear button trips the guard", async () => {
        await loadResolver("ldap1", "ldapresolver", ldapData);

        clearButtonOf(inputByLabel("Base DN")).click();
        await detectChangesStable();

        expect(component.hasChanges).toBe(true);
        expect(component.canSave).toBe(false);
      });

      it("the SQL Editable checkbox trips the guard", async () => {
        await loadResolver("sql1", "sqlresolver", {
          Driver: "mysql",
          Server: "db",
          Table: "users",
          Limit: 100,
          Map: "{}"
        });
        expect(component.hasChanges).toBe(false);

        checkboxInput("Edit user store").click();
        await detectChangesStable();

        expect(component.sqlResolver()!.isDirty()).toBe(true);
        expect(component.hasChanges).toBe(true);
        component.onCancel();
        expect(dialogService.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({ component: SaveAndExitDialogComponent })
        );
      });

      it("the SQL password hash select trips the guard", async () => {
        await loadResolver("sql1", "sqlresolver", { Driver: "mysql", Editable: "1", Limit: 100 });
        expect(component.hasChanges).toBe(false);

        fixture.debugElement
          .queryAll(By.directive(MatSelect))
          .find((d) => d.nativeElement.closest("mat-form-field")?.textContent?.includes("Password Hash"))!
          .injector.get(MatSelect)
          .options.find((o) => o.value === "SSHA")!
          .select();
        await detectChangesStable();

        expect(component.hasChanges).toBe(true);
      });

      it("the passwd clear button trips the guard", async () => {
        await loadResolver("pw1", "passwdresolver", { fileName: "/etc/passwd" });
        expect(component.hasChanges).toBe(false);

        clearButtonOf(fixture.nativeElement.querySelector("app-passwd-resolver input")).click();
        await detectChangesStable();

        expect(component.hasChanges).toBe(true);
      });

      it("the SCIM clear button trips the guard", async () => {
        await loadResolver("scim1", "scimresolver", {
          Authserver: "http://auth",
          Resourceserver: "http://res",
          Client: "c",
          Secret: "s",
          Mapping: "{}"
        });
        expect(component.hasChanges).toBe(false);

        clearButtonOf(fixture.nativeElement.querySelector("app-scim-resolver input")).click();
        await detectChangesStable();

        expect(component.hasChanges).toBe(true);
      });
    });
  });
});
