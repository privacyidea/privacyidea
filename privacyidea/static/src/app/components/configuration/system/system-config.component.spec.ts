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
import { provideLocationMocks } from "@angular/common/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialog } from "@angular/material/dialog";
import { MatSelect } from "@angular/material/select";
import { MatSnackBar } from "@angular/material/snack-bar";
import { By } from "@angular/platform-browser";
import { provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmtpServer, SmtpService } from "@services/smtp/smtp.service";
import { SystemService } from "@services/system/system.service";
import { MockContentService, MockNotificationService, MockPiResponse, MockSmtpService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of, throwError } from "rxjs";
import { SystemConfigComponent } from "./system-config.component";
import { SystemDocumentationDialogComponent } from "./system-documentation-dialog/system-documentation-dialog.component";

describe("SystemConfigComponent", () => {
  let component: SystemConfigComponent;
  let fixture: ComponentFixture<SystemConfigComponent>;
  let systemService: MockSystemService;
  let authService: MockAuthService;
  let notificationService: MockNotificationService;
  let pendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SystemConfigComponent],
      providers: [
        provideRouter([]),
        provideLocationMocks(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SystemConfigComponent);
    component = fixture.componentInstance;
    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    contentService.routeUrl.set(ROUTE_PATHS.CONFIGURATION_SYSTEM);

    fixture.detectChanges();
  });

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const el = (): HTMLElement => fixture.nativeElement;
  const textInput = (placeholder: string) =>
    el().querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;
  const checkboxInput = (index: number) => el().querySelectorAll<HTMLInputElement>("mat-checkbox input")[index];
  const type = async (input: HTMLInputElement, value: string) => {
    input.value = value;
    input.dispatchEvent(new Event("input"));
    await flush();
  };
  const blur = async (input: HTMLInputElement) => {
    input.dispatchEvent(new Event("blur"));
    await flush();
  };
  const loadConfig = async (config: Record<string, string>) => {
    systemService.systemConfig.set(config);
    await flush();
  };
  const lastSavedBody = (): Record<string, unknown> => {
    const calls = systemService.saveSystemConfig.mock.calls;
    return calls[calls.length - 1][0];
  };

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should load the known settings into the form model", () => {
    expect(component.model()).toEqual(
      expect.objectContaining({
        splitAtSign: true,
        IncFailCountOnFalsePin: false,
        no_auth_counter: true,
        PrependPin: false,
        AutoResync: true
      })
    );
    expect(component.systemConfigForm.splitAtSign().value()).toBe(true);
    expect(component.hasChanges()).toBe(false);
  });

  it("should render the loaded boolean settings in the checkboxes", () => {
    expect([0, 1, 2, 3, 4].map((index) => checkboxInput(index).checked)).toEqual([true, false, true, false, true]);
  });

  it("should send settings without a control back unchanged", async () => {
    component.saveSystemConfig();

    expect(lastSavedBody()).toEqual(
      expect.objectContaining({
        someOtherConfig: "test_value",
        ReturnSamlAttributes: "True",
        ReturnSamlAttributesOnFail: "False",
        UiLoginDisplayHelpButton: false,
        UiLoginDisplayRealmBox: true
      })
    );
  });

  it("sends the checkbox settings of a pristine form as JSON booleans, as before the form migration", () => {
    component.saveSystemConfig();

    expect(lastSavedBody()).toEqual(
      expect.objectContaining({
        splitAtSign: true,
        IncFailCountOnFalsePin: false,
        no_auth_counter: true,
        PrependPin: false,
        AutoResync: true
      })
    );
  });

  it("should derive SMTP identifiers from the configured servers", () => {
    expect(component.smtpIdentifiers()).toStrictEqual([]);

    const smtpService = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    smtpService.smtpServers.set([{ identifier: "myServer" }, { identifier: "otherServer" }] as SmtpServer[]);

    expect(component.smtpIdentifiers()).toStrictEqual(["myServer", "otherServer"]);
  });

  it("should offer to clear the SMTP identifier only while one is selected", async () => {
    const smtpField = Array.from<HTMLElement>(el().querySelectorAll("mat-form-field")).find((field) =>
      field.querySelector("mat-select")
    )!;
    expect(smtpField.querySelector("app-clear-button")).toBeNull();

    await loadConfig({ "recovery.identifier": "myServer" });
    expect(smtpField.querySelector("app-clear-button")).not.toBeNull();

    smtpField.querySelector<HTMLButtonElement>("app-clear-button button")!.click();
    await flush();
    expect(component.model()["recovery.identifier"]).toBe("");
    expect(component.systemConfigForm["recovery.identifier"]().dirty()).toBe(true);
    expect(smtpField.querySelector("app-clear-button")).toBeNull();
  });

  it("should write the picked SMTP server to the model", async () => {
    const smtpService = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    smtpService.smtpServers.set([{ identifier: "myServer" }, { identifier: "otherServer" }] as SmtpServer[]);
    await flush();

    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    select.open();
    await flush();
    (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
    await flush();

    expect(component.model()["recovery.identifier"]).toBe("otherServer");
    expect(component.hasChanges()).toBe(true);
  });

  it("should save system config successfully", () => {
    const saveSpy = jest.spyOn(systemService, "saveSystemConfig");
    const notificationSpy = jest.spyOn(notificationService, "success");

    component.saveSystemConfig();

    expect(saveSpy).toHaveBeenCalled();
    expect(notificationSpy).toHaveBeenCalledWith("System configuration saved successfully.");
  });

  it("should handle save system config error", () => {
    jest
      .spyOn(systemService, "saveSystemConfig")
      .mockReturnValueOnce(of(new MockPiResponse<Record<string, "insert" | "update">>({ result: { status: false } })));
    const notificationSpy = jest.spyOn(notificationService, "error");

    component.saveSystemConfig();

    expect(notificationSpy).toHaveBeenCalledWith("Failed to save system configuration.");
  });

  it("should handle save system config HTTP error", () => {
    jest.spyOn(systemService, "saveSystemConfig").mockReturnValueOnce(throwError(() => new Error("Network error")));
    const notificationSpy = jest.spyOn(notificationService, "error");

    component.saveSystemConfig();

    expect(notificationSpy).toHaveBeenCalledWith("Error saving system configuration.");
  });

  it("should delete user cache successfully", () => {
    const deleteSpy = jest.spyOn(systemService, "deleteUserCache");
    const notificationSpy = jest.spyOn(notificationService, "success");

    component.deleteUserCache();

    expect(deleteSpy).toHaveBeenCalled();
    expect(notificationSpy).toHaveBeenCalledWith("User cache deleted successfully.");
  });

  it("should handle delete user cache error", () => {
    jest
      .spyOn(systemService, "deleteUserCache")
      .mockReturnValueOnce(of(new MockPiResponse<{ status: boolean; deleted: number }>({ result: { status: false } })));
    const notificationSpy = jest.spyOn(notificationService, "error");

    component.deleteUserCache();

    expect(notificationSpy).toHaveBeenCalledWith("Failed to delete user cache.");
  });

  it("should handle delete user cache HTTP error", () => {
    jest.spyOn(systemService, "deleteUserCache").mockReturnValueOnce(throwError(() => new Error("Network error")));
    const notificationSpy = jest.spyOn(notificationService, "error");

    component.deleteUserCache();

    expect(notificationSpy).toHaveBeenCalledWith("Error deleting user cache.");
  });

  it("should handle openDocumentationDialog HTTP error", () => {
    jest.spyOn(systemService, "getDocumentation").mockReturnValueOnce(throwError(() => new Error("Network error")));
    const notificationSpy = jest.spyOn(notificationService, "error");

    (component as unknown as { openDocumentationDialog: () => void }).openDocumentationDialog();

    expect(notificationSpy).toHaveBeenCalledWith("Error loading system documentation.");
  });

  it("should open the documentation dialog once the documentation loads", () => {
    jest.spyOn(systemService, "getDocumentation").mockReturnValueOnce(of("<p>Docs</p>"));
    const dialog = TestBed.inject(MatDialog);
    const openSpy = jest.spyOn(dialog, "open");

    (component as unknown as { openDocumentationDialog: () => void }).openDocumentationDialog();

    expect(openSpy).toHaveBeenCalledWith(
      SystemDocumentationDialogComponent,
      expect.objectContaining({ data: { documentation: "<p>Docs</p>" } })
    );
  });

  it("should check config write permission", () => {
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    expect(component.hasConfigWritePermission()).toBe(true);

    jest.spyOn(authService, "actionAllowed").mockReturnValue(false);
    expect(component.hasConfigWritePermission()).toBe(false);
  });

  it("should reload system config when loadSystemConfig is called", () => {
    const reloadSpy = jest.spyOn(systemService.systemConfigResource, "reload");
    component.loadSystemConfig();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should register hasChanges, validChanges, and save in ngOnInit", () => {
    expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
    expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
    expect(pendingChangesService.registerSave).toHaveBeenCalled();
  });

  it("should report hasChanges from the model compared to the loaded settings", async () => {
    const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
    expect(fn()).toBe(false);

    checkboxInput(0).click();
    await flush();
    expect(fn()).toBe(true);

    checkboxInput(0).click();
    await flush();
    expect(fn()).toBe(false);
  });

  it("_saveAndReturn should call saveSystemConfig and resolve true on success", async () => {
    const saveSpy = jest.spyOn(systemService, "saveSystemConfig");
    const saveFn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
    const result = await saveFn();
    expect(saveSpy).toHaveBeenCalled();
    expect(notificationService.success).toHaveBeenCalledWith("System configuration saved successfully.");
    expect(result).toBe(true);
  });

  it("_saveAndReturn should resolve false when save returns status false", async () => {
    jest
      .spyOn(systemService, "saveSystemConfig")
      .mockReturnValueOnce(of(new MockPiResponse<Record<string, "insert" | "update">>({ result: { status: false } })));
    const saveFn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
    const result = await saveFn();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to save system configuration.");
    expect(result).toBe(false);
  });

  it("_saveAndReturn should resolve false on HTTP error", async () => {
    jest.spyOn(systemService, "saveSystemConfig").mockReturnValueOnce(throwError(() => new Error("Network error")));
    const saveFn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
    const result = await saveFn();
    expect(notificationService.error).toHaveBeenCalledWith("Error saving system configuration.");
    expect(result).toBe(false);
  });

  it("validChanges combines permission and form validity", async () => {
    const fn = (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    expect(fn()).toBe(true);
    jest.spyOn(authService, "actionAllowed").mockReturnValue(false);
    expect(fn()).toBe(false);

    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    await type(textInput("6"), "abc");
    expect(fn()).toBe(false);
  });

  it("ngOnDestroy clears all pending-changes registrations", () => {
    component.ngOnDestroy();
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });

  it("shows no input as 'undefined' for config keys the backend does not return", () => {
    const offenders = Array.from(fixture.nativeElement.querySelectorAll("input") as NodeListOf<HTMLInputElement>)
      .filter((input) => input.value === "undefined")
      .map((input) => input.getAttribute("placeholder") ?? input.getAttribute("name") ?? input.outerHTML);

    expect(offenders).toEqual([]);
  });

  it("shows the value the backend returns for a default token setting", () => {
    systemService.systemConfig.set({ DefaultOtpLen: "8" });
    fixture.detectChanges();

    const otpLenInput: HTMLInputElement = fixture.nativeElement.querySelector('input[placeholder="6"]');
    expect(otpLenInput.value).toBe("8");
  });

  describe("settings the backend does not hold", () => {
    beforeEach(async () => {
      await loadConfig({ DefaultOtpLen: "8", someOtherConfig: "kept" });
    });

    it("leaves every other control empty or unchecked", () => {
      expect(component.model()).toEqual({
        splitAtSign: false,
        IncFailCountOnFalsePin: false,
        no_auth_counter: false,
        PrependPin: false,
        AutoResync: false,
        AutoResyncTimeout: "",
        OverrideAuthorizationClient: "",
        UserCacheExpiration: "",
        failcounter_clear_timeout: "",
        DefaultChallengeValidityTime: "",
        DefaultCountWindow: "",
        DefaultMaxFailCount: "",
        DefaultOtpLen: "8",
        DefaultSyncWindow: "",
        "recovery.identifier": ""
      });
    });

    it("does not send an unset setting", () => {
      component.saveSystemConfig();

      expect(lastSavedBody()).toEqual({ DefaultOtpLen: "8", someOtherConfig: "kept" });
    });

    it("sends a setting the admin sets", async () => {
      await type(textInput("10"), "12");
      checkboxInput(1).click();
      await flush();
      component.saveSystemConfig();

      expect(lastSavedBody()).toEqual({
        DefaultOtpLen: "8",
        someOtherConfig: "kept",
        DefaultCountWindow: "12",
        IncFailCountOnFalsePin: true
      });
    });

    it("sends a cleared setting that the backend holds as an empty value", async () => {
      await type(textInput("6"), "");
      component.saveSystemConfig();

      expect(lastSavedBody()).toEqual({ DefaultOtpLen: "", someOtherConfig: "kept" });
    });

    it("keeps sending a setting once it was saved, so clearing it removes it", async () => {
      await type(textInput("10"), "12");
      component.saveSystemConfig();
      expect(component.hasChanges()).toBe(false);

      await type(textInput("10"), "");
      component.saveSystemConfig();

      expect(lastSavedBody()).toEqual(expect.objectContaining({ DefaultCountWindow: "" }));
    });

    it("skips a setting the backend returns as undefined", async () => {
      await loadConfig({ DefaultOtpLen: undefined as unknown as string, DefaultSyncWindow: "5" });

      expect(component.model().DefaultOtpLen).toBe("");
      component.saveSystemConfig();
      expect(lastSavedBody()).toEqual({ DefaultSyncWindow: "5" });
    });
  });

  describe("editing", () => {
    it("writes a typed value to the model and marks the field dirty", async () => {
      expect(component.systemConfigForm.DefaultSyncWindow().dirty()).toBe(false);

      await type(textInput("1000"), "500");

      expect(component.model().DefaultSyncWindow).toBe("500");
      expect(component.systemConfigForm.DefaultSyncWindow().dirty()).toBe(true);
      expect(component.hasChanges()).toBe(true);
    });

    it("clears the override authorization clients through the clear button", async () => {
      await type(textInput("127.0.0.1, 10.0.0.8"), "10.0.0.1");
      const clear = el().querySelector<HTMLButtonElement>("app-clearable-input app-clear-button button")!;

      clear.click();
      await flush();

      expect(component.model().OverrideAuthorizationClient).toBe("");
      expect(textInput("127.0.0.1, 10.0.0.8").value).toBe("");
    });

    it("disables the auto resync timeout while auto resync is off", async () => {
      const timeout = textInput("300");
      expect(timeout.disabled).toBe(false);

      checkboxInput(4).click();
      await flush();

      expect(component.model().AutoResync).toBe(false);
      expect(timeout.disabled).toBe(true);
    });

    it("keeps the auto resync timeout value while it is disabled", async () => {
      await type(textInput("300"), "120");
      checkboxInput(4).click();
      await flush();
      component.saveSystemConfig();

      expect(lastSavedBody()).toEqual(expect.objectContaining({ AutoResync: false, AutoResyncTimeout: "120" }));
    });

    it("discards edits when the settings are reloaded", async () => {
      await type(textInput("1000"), "500");
      await type(textInput("1000"), "x");
      await blur(textInput("1000"));
      expect(component.systemConfigForm.DefaultSyncWindow().touched()).toBe(true);

      await loadConfig({ DefaultSyncWindow: "7" });

      expect(component.model().DefaultSyncWindow).toBe("7");
      expect(component.hasChanges()).toBe(false);
      expect(component.systemConfigForm.DefaultSyncWindow().touched()).toBe(false);
    });
  });

  describe("numeric settings", () => {
    const numericKeys = [
      "failcounter_clear_timeout",
      "AutoResyncTimeout",
      "UserCacheExpiration",
      "DefaultOtpLen",
      "DefaultCountWindow",
      "DefaultMaxFailCount",
      "DefaultSyncWindow",
      "DefaultChallengeValidityTime"
    ] as const;
    // The numeric inputs in template order; the override clients input sits between them.
    const inputFor = (key: (typeof numericKeys)[number]): HTMLInputElement => {
      const inputs = Array.from(el().querySelectorAll<HTMLInputElement>("mat-form-field input:not([role])"));
      const withoutOverride = inputs.filter((input) => input.placeholder !== "127.0.0.1, 10.0.0.8");
      return withoutOverride[numericKeys.indexOf(key)];
    };

    it.each(numericKeys)("accepts an empty and a whole-number %s", async (key) => {
      await type(inputFor(key), "42");
      expect(component.model()[key]).toBe("42");
      expect(component.systemConfigForm[key]().valid()).toBe(true);
      await type(inputFor(key), "");
      expect(component.systemConfigForm[key]().valid()).toBe(true);
    });

    it.each(numericKeys)("rejects a non-numeric %s", async (key) => {
      await type(inputFor(key), "abc");
      expect(component.model()[key]).toBe("abc");
      expect(component.systemConfigForm[key]().errors()).toEqual([expect.objectContaining({ kind: "pattern" })]);
    });

    it.each(numericKeys)("shows the whole-number message of a non-numeric %s once touched", async (key) => {
      const input = inputFor(key);
      await type(input, "abc");
      await blur(input);

      expect(input.closest("mat-form-field")!.querySelector("mat-error")?.textContent).toContain("whole number");
    });

    it.each(["abc", "-1", "1.5", "1e3", " 5", "5 "])("rejects %p and shows the error once touched", async (bad) => {
      jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
      const input = textInput("1000");

      await type(input, bad);
      expect(component.systemConfigForm.DefaultSyncWindow().valid()).toBe(false);
      expect(el().querySelector("mat-error")).toBeNull();

      await blur(input);
      expect(el().querySelector("mat-error")?.textContent).toContain("whole number");
      expect(component.canSave()).toBe(false);
    });

    it("shows the errors of a stored invalid setting and disables Save", async () => {
      jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
      await loadConfig({ DefaultSyncWindow: "5.0" });

      expect(el().querySelector("mat-error")?.textContent).toContain("whole number");
      expect(component.canSave()).toBe(false);
      expect(el().querySelector<HTMLButtonElement>(".action-button-primary")!.disabled).toBe(true);
      expect(systemService.saveSystemConfig).not.toHaveBeenCalled();
    });

    it("disables Save while a typed value is invalid and enables it again once it is fixed", async () => {
      jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
      await flush();
      const saveButton = el().querySelector<HTMLButtonElement>(".action-button-primary")!;
      expect(saveButton.disabled).toBe(false);

      await type(textInput("1000"), "e");
      expect(saveButton.disabled).toBe(true);

      await type(textInput("1000"), "7");
      expect(saveButton.disabled).toBe(false);
    });

    it("does not save while a setting is invalid and shows every error", async () => {
      await type(textInput("1000"), "x");
      await type(textInput("6"), "y");

      component.saveSystemConfig();
      await flush();

      expect(systemService.saveSystemConfig).not.toHaveBeenCalled();
      expect(component.systemConfigForm.DefaultOtpLen().touched()).toBe(true);
      expect(el().querySelectorAll("mat-error").length).toBe(2);
    });

    it("does not save through the pending-changes save while a setting is invalid", async () => {
      await type(textInput("1000"), "x");
      const saveFn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;

      await expect(saveFn()).resolves.toBe(false);

      expect(systemService.saveSystemConfig).not.toHaveBeenCalled();
      expect(component.systemConfigForm.DefaultSyncWindow().touched()).toBe(true);
    });
  });
});
