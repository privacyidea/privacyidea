import { ComponentFixture, TestBed } from "@angular/core/testing";
import { UserNewResolverComponent } from "./user-new-resolver.component";
import { ResolverService } from "../../../services/resolver/resolver.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { Router } from "@angular/router";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";
import { MockNotificationService, MockPiResponse } from "../../../../testing/mock-services";
import { ResourceStatus, signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { FormControl, Validators } from "@angular/forms";

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
          provide: Router,
          useValue: {
            navigate: jest.fn(),
            navigateByUrl: jest.fn()
          }
        }
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

    const inputElement = fixture.nativeElement.querySelector("input[placeholder=\"/etc/passwd\"]");
    expect(inputElement?.value).toBe("/tmp/test");
  });

  it("should pre-fill form for sqlresolver when selected (edit mode)", async () => {
    const resolverName = "sql-res";
    const resolverData = {
      [resolverName]: {
        resolvername: resolverName,
        type: "sqlresolver",
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

    const dbInput = fixture.nativeElement.querySelector("input[placeholder=\"YourDatabase\"]");
    expect(dbInput?.value).toBe("testdb");
  });

  it("should re-fill form when resource reloads", async () => {
    const resolverName = "test-resolver";
    const initialData = {
      [resolverName]: {
        resolvername: resolverName,
        type: "passwdresolver",
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

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Connection test failed.")
    );
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
    const router = TestBed.inject(Router);

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("created"));
    expect(router.navigateByUrl).toHaveBeenCalled();
  });

  it("should show success on save in edit mode", async () => {
    resolverService.selectedResolverName.set("edit-res");
    const resolverData = {
      "edit-res": {
        resolvername: "edit-res",
        type: "passwdresolver",
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

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("updated"));
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
    component.updateAdditionalFormFields({ "fileName": new FormControl("", Validators.required) });
    component.onSave();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("fill in all required fields"));
  });

  it("should include additional fields in save payload", async () => {
    component.resolverName = "res";
    component.resolverType = "passwdresolver";
    component.updateAdditionalFormFields({ "fileName": new FormControl("/etc/passwd") });

    resolverService.postResolver.mockReturnValue(of(new MockPiResponse({ result: { status: true, value: 1 } })));
    component.onSave();

    expect(resolverService.postResolver).toHaveBeenCalledWith("res", expect.objectContaining({
      fileName: "/etc/passwd"
    }));
  });

  it("should execute test successfully", async () => {
    component.resolverType = "passwdresolver";
    const successResponse = new MockPiResponse<number, any>({
      result: { status: true, value: 1 }
    });
    resolverService.postResolverTest.mockReturnValue(of(successResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("test executed"));

    component.onQuickTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("test executed"));
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

  it("should update additional form fields", () => {
    const control = new FormControl("test");
    component.updateAdditionalFormFields({ "extra": control });
    expect(component["additionalFormFields"]["extra"]).toBe(control);
  });

  it("should apply SQL presets", () => {
    component.resolverType = "sqlresolver";
    const preset = component.sqlPresets[0];
    component.applySqlPreset(preset);
    expect(component.formData["Table"]).toBe(preset.table);
    expect(component.formData["Map"]).toBe(preset.map);
  });

  it("should apply LDAP presets", () => {
    component.resolverType = "ldapresolver";
    const preset = component.ldapPresets[0];
    component.applyLdapPreset(preset);
    expect(component.formData["LOGINNAMEATTRIBUTE"]).toBe(preset.loginName);
  });

  it("should validate before test", async () => {
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.resolverType = "" as any;
    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("select a resolver type"));

    component.resolverType = "passwdresolver";
    // passwdresolver has fileName as required, and it's currently empty if not set
    component.updateAdditionalFormFields({ "fileName": new FormControl("", Validators.required) });
    component.onTest();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("fill in all required fields"));
  });

  it("should include resolver name in test payload when in edit mode", async () => {
    resolverService.selectedResolverName.set("edit-res");
    const resolverData = { "edit-res": { resolvername: "edit-res", type: "passwdresolver", data: { fileName: "/etc/passwd" } } };
    (resolverService.selectedResolverResource as any).value.set({ result: { status: true, value: resolverData } });
    await detectChangesStable();

    resolverService.postResolverTest.mockReturnValue(of(new MockPiResponse({ result: { status: true, value: 1 } })));
    component.onTest();

    expect(resolverService.postResolverTest).toHaveBeenCalledWith(expect.objectContaining({
      resolver: "edit-res"
    }));
  });

  it("should handle type change", () => {
    component.resolverType = "sqlresolver";
    component.onTypeChange("sqlresolver");
    expect(component.resolverType).toBe("sqlresolver");
    expect(component.formData["Driver"]).toBe("mysql+pymysql");

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

    component.resolverType = "scimresolver";
    component.onTypeChange("scimresolver");
    expect(component.formData["Authserver"]).toBeDefined();

    component.resolverType = "httpresolver";
    component.onTypeChange("httpresolver");
    expect(component.formData["endpoint"]).toBeDefined();

    component.resolverType = "passwdresolver";
    component.onTypeChange("passwdresolver");
    expect(component.formData["fileName"]).toBe("/etc/passwd");
  });
});
