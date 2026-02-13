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
import { UserNewResolverComponent } from "./user-new-resolver.component";
import { ResolverService } from "../../../services/resolver/resolver.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { ActivatedRoute, Router } from "@angular/router";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";
import { MockNotificationService, MockPiResponse } from "../../../../testing/mock-services";
import { ResourceStatus, signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ROUTE_PATHS } from "../../../route_paths";

global.IntersectionObserver = class IntersectionObserver {
  constructor() {}

  disconnect() {}

  observe() {}

  unobserve() {}

  takeRecords() {
    return [];
  }
} as any;

describe("UserNewResolverComponent", () => {
  let component: UserNewResolverComponent;
  let fixture: ComponentFixture<UserNewResolverComponent>;
  let resolverService: MockResolverService;

  async function detectChangesStable() {
    fixture.detectChanges(false);
    await fixture.whenStable();
    fixture.detectChanges(false);
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserNewResolverComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: (key: string) => "" })
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
        },
        {
          provide: MatDialogRef,
          useValue: {
            close: jest.fn(),
            backdropClick: jest.fn().mockReturnValue(of()),
            keydownEvents: jest.fn().mockReturnValue(of())
          }
        },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserNewResolverComponent);
    component = fixture.componentInstance;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
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
    const resourceStatus = signal(ResourceStatus.Resolved);

    (resolverService.selectedResolverResource as any).value = resourceValue;
    (resolverService.selectedResolverResource as any).status = resourceStatus;

    await detectChangesStable();

    expect(component.isEditMode).toBeTruthy();
    expect(component.resolverName).toBe(resolverName);
    expect(component.resolverType).toBe("passwdresolver");
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
    const resourceStatus = signal(ResourceStatus.Resolved);

    (resolverService.selectedResolverResource as any).value = resourceValue;
    (resolverService.selectedResolverResource as any).status = resourceStatus;

    await detectChangesStable();

    expect(component.isEditMode).toBeTruthy();
    expect(component.resolverType).toBe("sqlresolver");

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
    const resourceStatus = signal(ResourceStatus.Resolved);

    (resolverService.selectedResolverResource as any).value = resourceValue;
    (resolverService.selectedResolverResource as any).status = resourceStatus;

    await detectChangesStable();
    expect(component.formData["fileName"]).toBe("/initial");

    resourceStatus.set(ResourceStatus.Reloading);
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
    resourceStatus.set(ResourceStatus.Resolved);

    await detectChangesStable();
    expect(component.formData["fileName"]).toBe("/updated");
  });

  it("should show error and not redirect when postResolver returns status true but value -1", async () => {
    await detectChangesStable();

    const resolverName = "test-error";
    component.resolverName = resolverName;
    component.resolverType = "sqlresolver";

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
    const router = TestBed.inject(Router);

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Unable to connect to database.")
    );
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(component.resolverName).toBe(resolverName);
  });

  it("should show error when postResolverTest returns status true but value -1", async () => {
    await detectChangesStable();

    component.resolverType = "sqlresolver";

    const errorResponse = new MockPiResponse<number, { description: string }>({
      result: {
        status: true,
        value: -1
      },
      detail: {
        description: "Connection test failed."
      }
    });

    resolverService.postResolverTest.mockReturnValue(of(errorResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Connection test failed."));
  });

  it("should show success on save", async () => {
    await detectChangesStable();
    component.resolverName = "new-res";
    component.resolverType = "passwdresolver";

    const successResponse = new MockPiResponse<number, any>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolver.mockReturnValue(of(successResponse));

    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    const dialogRef = TestBed.inject(MatDialogRef);

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("created"));
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it("should show success on save in edit mode", async () => {
    resolverService.selectedResolverName.set("edit-res");
    const resolverData = {
      "edit-res": {
        resolvername: "edit-res",
        type: "passwdresolver",
        censor_keys: [],
        data: { fileName: "/etc/passwd" }
      }
    };
    (resolverService.selectedResolverResource as any).value.set({
      result: { status: true, value: resolverData }
    });
    await detectChangesStable();

    const successResponse = new MockPiResponse<number, any>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolver.mockReturnValue(of(successResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    const dialogRef = TestBed.inject(MatDialogRef);

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("updated"));
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it("should show error on save when subscription fails", async () => {
    component.resolverName = "err-res";
    component.resolverType = "passwdresolver";
    const errorResponse = { message: "Network error", error: { result: { error: { message: "Detailed error" } } } };
    resolverService.postResolver.mockReturnValue({
      subscribe: (obs: any) => {
        obs.error(errorResponse);
        return { add: jest.fn() };
      }
    } as any);
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Detailed error"));
  });

  it("should validate before save", async () => {
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.resolverName = "";
    component.onSave();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("enter a resolver name"));

    component.resolverName = "res";
    component.resolverType = "" as any;
    component.onSave();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    component.resolverType = "passwdresolver";
    await detectChangesStable();
    component.passwdResolver()?.filenameControl.setValue("");
    component.onSave();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("fill in all required fields")
    );
  });

  it("should include additional fields in save payload", async () => {
    component.resolverName = "res";
    component.resolverType = "passwdresolver";
    await detectChangesStable();
    component.passwdResolver()?.filenameControl.setValue("/etc/passwd");

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
    component.resolverType = "passwdresolver";
    const successResponse = new MockPiResponse<number, any>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolverTest.mockReturnValue(of(successResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Resolver test executed:"),
      20000
    );

    component.onQuickTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Resolver test executed:"),
      20000
    );
  });

  it("should show error on test when subscription fails", async () => {
    component.resolverType = "passwdresolver";
    const errorResponse = { message: "Network error" };
    resolverService.postResolverTest.mockReturnValue({
      subscribe: (obs: any) => {
        obs.error(errorResponse);
        return { add: jest.fn() };
      }
    } as any);
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("should validate before test", async () => {
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.resolverType = "" as any;
    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    component.resolverType = "passwdresolver";
    await detectChangesStable();
    component.passwdResolver()?.filenameControl.setValue("");
    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("fill in all required fields")
    );
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
    (resolverService.selectedResolverResource as any).value.set({ result: { status: true, value: resolverData } });
    await detectChangesStable();

    resolverService.postResolverTest.mockReturnValue(of(new MockPiResponse({ result: { status: true, value: 1 } })));
    component.onTest();

    expect(resolverService.postResolverTest).toHaveBeenCalledWith(
      expect.objectContaining({
        resolver: "edit-res"
      })
    );
  });

  it("should handle type change", () => {
    component.resolverType = "sqlresolver";
    component.onTypeChange("sqlresolver");
    expect(component.resolverType).toBe("sqlresolver");

    component.resolverType = "ldapresolver";
    component.onTypeChange("ldapresolver");
    expect(component.resolverType).toBe("ldapresolver");
    expect(component.formData["TLS_VERSION"]).toBe("TLSv1_3");

    component.resolverType = "entraidresolver";
    component.onTypeChange("entraidresolver");
    expect(component.formData["base_url"]).toBeDefined();

    component.resolverType = "keycloakresolver";
    component.onTypeChange("keycloakresolver");
    expect(component.formData["config_authorization"]).toBeDefined();

    component.resolverType = "httpresolver";
    component.onTypeChange("httpresolver");
    expect(component.formData["responseMapping"]).toBeUndefined();

    component.resolverType = "passwdresolver";
    component.onTypeChange("passwdresolver");
    expect(component.formData["fileName"]).toBe("/etc/passwd");
  });

  it("should initialize from dialog data resolver object", async () => {
    const resolver = {
      resolvername: "dialog-resolver",
      type: "ldapresolver" as any,
      censor_keys: [],
      data: { LDAPURI: "ldap://localhost" }
    };

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [UserNewResolverComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
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
        },
        {
          provide: MatDialogRef,
          useValue: {
            close: jest.fn(),
            backdropClick: jest.fn().mockReturnValue(of()),
            keydownEvents: jest.fn().mockReturnValue(of())
          }
        },
        { provide: MAT_DIALOG_DATA, useValue: { resolver } }
      ]
    }).compileComponents();

    const fixtureDialog = TestBed.createComponent(UserNewResolverComponent);
    const componentDialog = fixtureDialog.componentInstance;

    expect(componentDialog.resolverName).toBe("dialog-resolver");
    expect(componentDialog.resolverType).toBe("ldapresolver");
    expect(componentDialog.formData["LDAPURI"]).toBe("ldap://localhost");
    expect(componentDialog.isEditMode).toBeTruthy();
  });
});
