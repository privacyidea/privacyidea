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

(globalThis as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver = class IntersectionObserver {
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

    const inputElement = fixture.nativeElement.querySelector('input[placeholder="/etc/passwd"]');
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

    const dbInput = fixture.nativeElement.querySelector('input[placeholder="YourDatabase"]');
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
    component.resolverType.set("sqlresolver");

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

    component.resolverType.set("sqlresolver");

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
    component.resolverType.set("passwdresolver");

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
    component.resolverType.set("passwdresolver");
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
    component.resolverType.set("" as unknown as ResolverType);
    success = await component.onSave();
    expect(success).toBe(false);
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    component.resolverType.set("passwdresolver");
    await detectChangesStable();
    component.passwdResolver()?.model.set({ fileName: "" });
    success = await component.onSave();
    expect(success).toBe(false);
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("fill in all required fields"));
  });

  it("should include additional fields in save payload", async () => {
    component.resolverNameModel.set({ resolverName: "res" });
    component.resolverType.set("passwdresolver");
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
    component.resolverType.set("passwdresolver");
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
    component.resolverType.set("passwdresolver");
    fixture.detectChanges();

    const errorResponse = { message: "Network error" };

    resolverService.postResolverTest.mockReturnValue(throwError(() => errorResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();

    expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("should validate before test", async () => {
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.resolverType.set("" as unknown as ResolverType);
    component.onTest();
    expect(notificationService.warning).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    component.resolverType.set("passwdresolver");
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
    component.onTypeChange("sqlresolver");
    expect(component.resolverType()).toBe("sqlresolver");

    component.onTypeChange("ldapresolver");
    expect(component.resolverType()).toBe("ldapresolver");
    expect(component.formData["TLS_VERSION"]).toBe("TLSv1_3");

    component.onTypeChange("entraidresolver");
    expect(component.formData).toEqual({});

    component.onTypeChange("keycloakresolver");
    expect(component.formData).toEqual({});

    component.onTypeChange("httpresolver");
    expect(component.formData["responseMapping"]).toBeUndefined();

    component.onTypeChange("passwdresolver");
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
    component.resolverType.set("passwdresolver");
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
    component.resolverType.set("passwdresolver");
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

    component.testUsername.set("test");
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
});
