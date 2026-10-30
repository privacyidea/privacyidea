import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute } from "@angular/router";
import { NotificationService } from "@services/notification/notification.service";
import { SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { SystemService } from "@services/system/system.service";
import { MockPendingChangesService, MockPiResponse, MockSystemService } from "@testing/mock-services";
import { Observable, of, throwError } from "rxjs";
import { TokenTypeConfigComponent } from "./token-type-config.component";
import { By } from "@angular/platform-browser";
import { EmailConfigComponent } from "./token-types/email-config/email-config.component";
import { RadiusConfigComponent } from "./token-types/radius-config/radius-config.component";
import { SmsConfigComponent } from "./token-types/sms-config/sms-config.component";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  EMAIL_VALIDITY_TIME_KEY,
  HOTP_HASHLIB,
  QUESTION_NUMBER_OF_ANSWERS,
  REMOTE_VERIFY_SSL,
  SMS_PROVIDER_TIMEOUT,
  TIQR_OCRASUITE,
  TIQR_REG_SERVER,
  TOTP_TIME_WINDOW,
  U2F_APP_ID,
  YUBICO_ID,
  YUBICO_SECRET,
  YUBICO_URL
} from "@constants/token.constants";

class MockActivatedRoute {
  fragment: Observable<string | undefined> = of();
  queryParams: Observable<Record<string, unknown>> = of({});
}

describe("TokenTypeConfigComponent", () => {
  let component: TokenTypeConfigComponent;
  let fixture: ComponentFixture<TokenTypeConfigComponent>;
  let httpMock: HttpTestingController;
  let activatedRoute: MockActivatedRoute;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTypeConfigComponent],
      providers: [
        { provide: ActivatedRoute, useClass: MockActivatedRoute },
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        {
          provide: SmsGatewayService,
          useValue: {
            smsGateways: signal([]),
            canListSmsGateways: signal(true),
            smsGatewayResource: { value: () => ({ result: { value: [] } }) }
          }
        },
        {
          provide: SmtpService,
          useValue: {
            smtpServers: signal([]),
            canListSmtpServers: signal(true),
            smtpServerResource: { value: () => ({ result: { value: {} } }) }
          }
        },
        {
          provide: NotificationService,
          useValue: { success: jest.fn(), error: jest.fn(), warning: jest.fn(), handleResourceError: jest.fn() }
        },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    activatedRoute = TestBed.inject(ActivatedRoute) as unknown as MockActivatedRoute;
    jest.spyOn(document, "getElementById").mockReturnValue({ scrollIntoView: jest.fn() } as unknown as HTMLElement);

    fixture = TestBed.createComponent(TokenTypeConfigComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("list rights of the SMS, e-mail and RADIUS panels", () => {
    const listable = () => ({
      sms: fixture.debugElement.query(By.directive(SmsConfigComponent)).componentInstance.smsGatewaysListable(),
      email: fixture.debugElement.query(By.directive(EmailConfigComponent)).componentInstance.smtpServersListable(),
      radius: fixture.debugElement.query(By.directive(RadiusConfigComponent)).componentInstance.radiusServersListable()
    });

    it("should let every panel list its servers when all rights are present", () => {
      expect(listable()).toEqual({ sms: true, email: true, radius: true });
    });

    it("should pass each service's list right to its own panel only", () => {
      const smsService = TestBed.inject(SmsGatewayService) as unknown as {
        canListSmsGateways: WritableSignal<boolean>;
      };
      const smtpService = TestBed.inject(SmtpService) as unknown as { canListSmtpServers: WritableSignal<boolean> };
      const systemService = TestBed.inject(SystemService) as unknown as MockSystemService;

      smsService.canListSmsGateways.set(false);
      fixture.detectChanges();
      expect(listable()).toEqual({ sms: false, email: true, radius: true });

      smsService.canListSmsGateways.set(true);
      smtpService.canListSmtpServers.set(false);
      fixture.detectChanges();
      expect(listable()).toEqual({ sms: true, email: false, radius: true });

      smtpService.canListSmtpServers.set(true);
      systemService.canListRadiusServers.set(false);
      fixture.detectChanges();
      expect(listable()).toEqual({ sms: true, email: true, radius: false });
    });
  });

  it("should initialize formData from systemConfig", () => {
    expect(component.formData().values["splitAtSign"]).toBe("True");
    expect(component.formData().values["someOtherConfig"]).toBe("test_value");
  });

  it("should calculate questionKeys correctly", () => {
    component.formData.set({
      values: { "question.question.1": "Q1", "question.question.2": "Q2", other: "val" },
      verifySsl: false
    });
    expect(component.questionKeys()).toEqual(["question.question.1", "question.question.2"]);
  });

  it("should calculate yubikeyApiIds correctly", () => {
    component.formData.set({
      values: { "yubikey.apiid.ID1": "KEY1", "yubikey.apiid.ID2": "KEY2", other: "val" },
      verifySsl: false
    });
    expect(component.yubikeyApiIds()).toEqual(["yubikey.apiid.ID1", "yubikey.apiid.ID2"]);
  });

  it("should call saveSystemConfig on save", async () => {
    const systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    const saveSpy = jest.spyOn(systemService, "saveSystemConfig");
    const reloadSpy = jest.spyOn(systemService.systemConfigResource, "reload");

    await component.save();

    expect(saveSpy).toHaveBeenCalledWith(systemService.systemConfig());
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should notify an error when saveSystemConfig reports failure", async () => {
    const systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    const notificationService = TestBed.inject(NotificationService);
    jest
      .spyOn(systemService, "saveSystemConfig")
      .mockReturnValueOnce(of(new MockPiResponse<Record<string, "insert" | "update">>({ result: { status: false } })));

    await component.save();

    expect(notificationService.error).toHaveBeenCalledWith("Failed to save token configuration.");
  });

  it("should notify an error when saveSystemConfig throws", async () => {
    const systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    const notificationService = TestBed.inject(NotificationService);
    jest.spyOn(systemService, "saveSystemConfig").mockReturnValueOnce(throwError(() => new Error("Network error")));

    await component.save();

    expect(notificationService.error).toHaveBeenCalledWith("Error saving token configuration.");
  });

  it("should add an empty question to formData without saving", () => {
    const saveSpy = jest.spyOn(component, "save");
    const before = component.questionKeys().length;

    component.addQuestion();

    const questionKeys = component.questionKeys();
    expect(questionKeys.length).toBe(before + 1);
    const addedKey = questionKeys[questionKeys.length - 1];
    expect(component.formData().values[addedKey]).toBe("");
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it("should update formData and pendingDeletes but not call service on deleteSystemEntry", () => {
    const systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    const deleteSpy = jest.spyOn(systemService, "deleteSystemConfig");
    const reloadSpy = jest.spyOn(systemService.systemConfigResource, "reload");

    const entryToDelete = "yubikey.apiid.123";
    const entryToKeep = "yubikey.apiid.456";

    // Set initial config so it's tracked for deferred deletion
    systemService.systemConfig.set({ [entryToDelete]: "123", [entryToKeep]: "456" });
    fixture.detectChanges();

    component.deleteSystemEntry(entryToDelete);

    expect(deleteSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(component.formData().values).not.toHaveProperty(entryToDelete);
    expect(component.formData().values[entryToKeep]).toEqual("456");
    expect(component.pendingDeletes().has(entryToDelete)).toBe(true);
  });

  describe("deleting the only question", () => {
    let systemService: MockSystemService;

    beforeEach(() => {
      systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
      systemService.systemConfig.set({
        "question.question.0": "Q0",
        [QUESTION_NUMBER_OF_ANSWERS]: "1"
      });
      fixture.detectChanges();
      // Deleting the only question re-adds an empty slot via reconcile (reusing index 0)
      // and queues the backend key for deletion.
      component.deleteQuestion("question.question.0");
    });

    it("queues the backend key for deletion without calling the service", () => {
      expect(component.pendingDeletes().has("question.question.0")).toBe(true);
      expect(systemService.deleteSystemConfig).not.toHaveBeenCalled();
    });

    it("saves a new question in the reused slot instead of deleting its key", async () => {
      component.configForm.values["question.question.0"]().controlValue.set("New question");
      fixture.detectChanges();

      expect(await component.save()).toBe(true);

      expect(systemService.deleteSystemConfig).not.toHaveBeenCalledWith("question.question.0");
      expect(systemService.saveSystemConfig.mock.calls[0][0]["question.question.0"]).toBe("New question");
    });

    it("refuses to save while the empty slot is required", async () => {
      expect(await component.save()).toBe(false);

      expect(systemService.deleteSystemConfig).not.toHaveBeenCalled();
      expect(systemService.saveSystemConfig).not.toHaveBeenCalled();
    });

    it("deletes the backend key and does not write it back as an empty string once no answer is required", async () => {
      component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("0");
      fixture.detectChanges();

      expect(await component.save()).toBe(true);

      expect(systemService.deleteSystemConfig).toHaveBeenCalledWith("question.question.0");
      expect(systemService.saveSystemConfig.mock.calls[0][0]).not.toHaveProperty("question.question.0");
    });
  });

  it("should create new yubikey key", async () => {
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "", generateKey: true });

    const req = httpMock.expectOne((req) => req.url.endsWith("/system/random?len=20&encode=b64"));
    expect(req.request.method).toBe("GET");
    req.flush({ result: { status: true, value: "new-random-key" } });

    await promise;
    expect(component.formData().values["yubikey.apiid.myID"]).toBe("new-random-key");
  });

  it("should only add, but not generate api key", async () => {
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "123", generateKey: false });

    httpMock.expectNone((req) => req.url.endsWith("/system/random?len=20&encode=b64"));

    await promise;
    expect(component.formData().values["yubikey.apiid.myID"]).toBe("123");
  });

  it("generateKey wins over apiKey if both are provided", async () => {
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "123", generateKey: true });

    const req = httpMock.expectOne((req) => req.url.endsWith("/system/random?len=20&encode=b64"));
    expect(req.request.method).toBe("GET");
    req.flush({ result: { status: true, value: "new-random-key" } });

    await promise;
    expect(component.formData().values["yubikey.apiid.myID"]).toBe("new-random-key");
  });

  it("should handle error in yubikeyCreateNewKey", async () => {
    const notificationService = component.notificationService;
    const snackBarSpy = jest.spyOn(notificationService, "error");
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "", generateKey: true });

    const req = httpMock.expectOne((req) => req.url.endsWith("/system/random?len=20&encode=b64"));
    req.error(new ProgressEvent("error"));

    await promise;
    expect(snackBarSpy).toHaveBeenCalledWith(expect.stringContaining("Failed to generate API key"));
  });

  it("should use fallback values if init data is missing", () => {
    // We can't easily mock the computed signal of the already created component if it's already initialized.
    // But we can check that it has the values from MockSystemService (which has init data).
    expect(component.hashLibs()).toEqual(["sha1", "sha256", "sha512"]);
    expect(component.totpSteps()).toEqual(["30", "60"]);
  });

  describe("Fragment handling and panel expansion", () => {
    it("expandedPanel should be null if no fragment is defined", () => {
      expect(component.expandedPanel).toBeNull();
    });

    it("should not scroll if expandedPanel is null", () => {
      const scrollSpy = jest.fn();
      jest.spyOn(document, "getElementById").mockReturnValue({ scrollIntoView: scrollSpy } as unknown as HTMLElement);
      component.ngAfterViewInit();
      expect(scrollSpy).not.toHaveBeenCalled();
    });

    describe("Fragment defined", () => {
      beforeEach(async () => {
        activatedRoute.fragment = of("yubico");
        fixture = TestBed.createComponent(TokenTypeConfigComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
      });

      it("should set expandedPanel when fragment is defined", () => {
        expect(component.expandedPanel).toBe("yubico");
      });

      it("expands only the referenced panel", () => {
        const expanded = (selector: string) =>
          fixture.nativeElement.querySelector(`${selector} mat-expansion-panel`).classList.contains("mat-expanded");

        expect(expanded("app-yubico-config")).toBe(true);
        expect(expanded("app-sms-config")).toBe(false);
        expect(expanded("app-radius-config")).toBe(false);
        expect(expanded("app-questionnaire-config")).toBe(false);
      });

      it("should scroll to referenced panel when expandedPanel is defined", () => {
        const scrollSpy = jest.fn();
        jest.spyOn(document, "getElementById").mockReturnValue({ scrollIntoView: scrollSpy } as unknown as HTMLElement);
        component.ngAfterViewInit();
        expect(scrollSpy).toHaveBeenCalledWith({ behavior: "smooth" });
      });
    });
  });

  describe("missing config keys", () => {
    it("shows no input as 'undefined' for keys the backend does not return", () => {
      const inputs = Array.from(fixture.nativeElement.querySelectorAll("input") as NodeListOf<HTMLInputElement>);
      expect(inputs.length).toBeGreaterThan(0);

      const offenders = inputs
        .filter((input) => input.value === "undefined")
        .map((input) => input.getAttribute("placeholder") ?? input.getAttribute("name") ?? input.outerHTML);

      expect(offenders).toEqual([]);
    });

    it("shows the value the backend returns for a token type setting", () => {
      const systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
      systemService.systemConfig.set({ [TIQR_REG_SERVER]: "https://pi.example/ttype/tiqr" });
      fixture.detectChanges();

      const regServerInput: HTMLInputElement = fixture.nativeElement.querySelector(
        'input[placeholder="http://pi.server/ttype/tiqr"]'
      );
      expect(regServerInput.value).toBe("https://pi.example/ttype/tiqr");
    });
  });

  describe("form", () => {
    let systemService: MockSystemService;
    let pendingChanges: MockPendingChangesService;

    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const query = <T extends HTMLElement = HTMLInputElement>(selector: string) =>
      fixture.nativeElement.querySelector(selector) as T;
    const typeInto = async (selector: string, value: string) => {
      const input = query(selector);
      input.value = value;
      input.dispatchEvent(new Event("input"));
      await flush();
    };
    const savedPayload = () => systemService.saveSystemConfig.mock.calls[0][0] as Record<string, string>;
    const saveButton = () => query<HTMLButtonElement>(".sticky-header button.action-button-primary");

    beforeEach(() => {
      systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
      pendingChanges = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    });

    it("registers the validity of the form for the unsaved-changes guard", () => {
      expect(pendingChanges.registerValidChanges).toHaveBeenCalledTimes(1);
      const isValid = pendingChanges.registerValidChanges.mock.calls[0][0] as () => boolean;
      expect(isValid()).toBe(true);
      component.configForm.values[TIQR_OCRASUITE]().controlValue.set("suite");
      expect(isValid()).toBe(false);
    });

    describe("hasChanges", () => {
      it("is false for the loaded config", () => {
        expect(component.hasChanges()).toBe(false);
      });

      it("is true after an edit and false again once the edit is reverted", async () => {
        const original = component.formData().values[TIQR_OCRASUITE];
        await typeInto('input[placeholder="https://www.privacyidea.org"]', "https://pi.example");
        await typeInto('input[placeholder="https://www.privacyidea.org"]', original);
        expect(component.hasChanges()).toBe(false);

        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("");
        expect(component.hasChanges()).toBe(false);
      });

      it("is true after a value is typed into a panel the backend has no entry for", async () => {
        await typeInto('input[placeholder="https://pi.server.com"]', "https://pi.example.com");
        expect(component.hasChanges()).toBe(true);
      });

      it("is true after the SSL box is checked and false after it is unchecked", () => {
        component.configForm.verifySsl().controlValue.set(true);
        expect(component.hasChanges()).toBe(true);
        component.configForm.verifySsl().controlValue.set(false);
        expect(component.hasChanges()).toBe(false);
      });

      it("is true while a deletion is pending", () => {
        component.pendingDeletes.set(new Set(["yubikey.apiid.X"]));
        expect(component.hasChanges()).toBe(true);
      });
    });

    describe("save button", () => {
      it("is disabled for an unchanged config", () => {
        expect(saveButton().disabled).toBe(true);
      });

      it("is enabled after a valid edit", async () => {
        jest.spyOn(component.authService, "actionAllowed").mockReturnValue(true);
        await typeInto('input[placeholder="https://pi.server.com"]', "https://pi.example.com");
        expect(saveButton().disabled).toBe(false);
      });

      it("is disabled while a partly filled panel has an empty required entry", async () => {
        jest.spyOn(component.authService, "actionAllowed").mockReturnValue(true);
        await typeInto('input[placeholder="https://www.privacyidea.org"]', "https://pi.example");
        expect(component.configForm().valid()).toBe(false);
        expect(saveButton().disabled).toBe(true);
      });
    });

    describe("required entries of a partly filled panel", () => {
      it("shows no error for an empty panel", () => {
        expect(fixture.nativeElement.querySelectorAll("mat-error").length).toBe(0);
        expect(component.configForm().valid()).toBe(true);
      });

      it("blocks the save, touches the fields and shows the errors", async () => {
        await typeInto('input[placeholder="https://www.privacyidea.org"]', "https://pi.example");

        expect(await component.save()).toBe(false);
        await flush();

        expect(systemService.saveSystemConfig).not.toHaveBeenCalled();
        expect(component.configForm.values[TIQR_REG_SERVER]().touched()).toBe(true);
        const tiqr = query("app-tiqr-config");
        expect(tiqr.querySelectorAll("mat-error").length).toBe(2);
      });

      it("lets the other panels be saved while a panel is empty", async () => {
        await typeInto('input[placeholder="https://pi.server.com"]', "https://pi.example.com");

        expect(await component.save()).toBe(true);

        expect(savedPayload()[U2F_APP_ID]).toBe("https://pi.example.com");
        expect(savedPayload()).not.toHaveProperty(TIQR_REG_SERVER);
      });
    });

    describe("a Yubico panel without a URL", () => {
      beforeEach(() => {
        jest.spyOn(component.authService, "actionAllowed").mockReturnValue(true);
        systemService.systemConfig.set({ [YUBICO_ID]: "12345", [YUBICO_SECRET]: "secret" });
        fixture.detectChanges();
      });

      it("does not block saving a change to another panel", async () => {
        component.configForm.values[HOTP_HASHLIB]().controlValue.set("sha256");
        await flush();

        expect(component.configForm().valid()).toBe(true);
        expect(saveButton().disabled).toBe(false);
        expect(query(".save-blocked-hint")).toBeNull();
        expect(await component.save()).toBe(true);
        expect(savedPayload()[HOTP_HASHLIB]).toBe("sha256");
        expect(savedPayload()).not.toHaveProperty(YUBICO_URL);
      });
    });

    describe("an incomplete panel", () => {
      beforeEach(() => {
        jest.spyOn(component.authService, "actionAllowed").mockReturnValue(true);
        systemService.systemConfig.set({ [YUBICO_ID]: "12345" });
        component.configForm.values[HOTP_HASHLIB]().controlValue.set("sha256");
        fixture.detectChanges();
      });

      it("marks the header of the panel and says why Save is disabled", async () => {
        await flush();

        expect(saveButton().disabled).toBe(true);
        expect(query(".save-blocked-hint")?.textContent).toContain("Incomplete");
        expect(query("app-yubico-config .panel-incomplete")?.textContent).toContain("Incomplete");
        expect(query("app-hotp-config .panel-incomplete")).toBeNull();
      });

      it("opens the incomplete panel and drops the markers once the panel is complete", async () => {
        await flush();
        expect(query("app-yubico-config mat-expansion-panel").classList).toContain("mat-expanded");

        await typeInto('input[placeholder="API Key"]', "secret");

        expect(query("app-yubico-config .panel-incomplete")).toBeNull();
        expect(query(".save-blocked-hint")).toBeNull();
        expect(saveButton().disabled).toBe(false);
      });
    });

    describe("an incomplete panel and the open-all toggle", () => {
      it("closes the opened incomplete panel with the other panels", async () => {
        jest.spyOn(component.authService, "actionAllowed").mockReturnValue(true);
        systemService.systemConfig.set({ [YUBICO_ID]: "12345" });
        await flush();
        const yubico = () => query("app-yubico-config mat-expansion-panel");
        expect(yubico().classList).toContain("mat-expanded");

        component.toggleAllPanels();
        await flush();
        expect(yubico().classList).toContain("mat-expanded");

        component.toggleAllPanels();
        await flush();
        expect(yubico().classList).not.toContain("mat-expanded");
      });
    });

    describe("an emptied entry the backend defaults", () => {
      it("is not a change while the backend holds the entry empty", async () => {
        systemService.systemConfig.set({ [YUBICO_URL]: "", [HOTP_HASHLIB]: "sha1" });
        await flush();

        expect(component.hasChanges()).toBe(false);
        expect(saveButton().disabled).toBe(true);

        component.configForm.values[HOTP_HASHLIB]().controlValue.set("sha256");
        await flush();
        await component.save();

        expect(systemService.deleteSystemConfig).toHaveBeenCalledWith(YUBICO_URL);
      });

      it("is deleted in the backend instead of saved as an empty string", async () => {
        systemService.systemConfig.set({ [YUBICO_URL]: "https://yubico.example" });
        fixture.detectChanges();

        component.configForm.values[YUBICO_URL]().controlValue.set("");
        await flush();
        expect(component.hasChanges()).toBe(true);
        await component.save();

        expect(systemService.deleteSystemConfig).toHaveBeenCalledWith(YUBICO_URL);
        expect(savedPayload()).not.toHaveProperty(YUBICO_URL);
      });
    });

    describe("save payload", () => {
      it("saves the AppID typed into the U2F panel", async () => {
        await typeInto('input[placeholder="https://pi.server.com"]', "https://pi.example.com");

        await component.save();

        expect(savedPayload()[U2F_APP_ID]).toBe("https://pi.example.com");
      });

      it("shows the warnings of the U2F panel for the typed AppID", async () => {
        await typeInto('input[placeholder="https://pi.server.com"]', "http://pi.example.com/");

        expect(query("app-u2f-config").querySelectorAll(".alert-warning").length).toBe(2);
      });

      it("saves the SSL flag the box was checked to as True", async () => {
        query<HTMLInputElement>("app-remote-config input[type=checkbox]").click();
        await flush();

        await component.save();

        expect(savedPayload()[REMOTE_VERIFY_SSL]).toBe("True");
      });

      describe("a cleared number input", () => {
        const cases: [string, string, string, string][] = [
          ["email validity time", EMAIL_VALIDITY_TIME_KEY, "120", "app-email-config input[type=number]"],
          ["SMS provider timeout", SMS_PROVIDER_TIMEOUT, "300", "app-sms-config input[type=number]"],
          ["TOTP time window", TOTP_TIME_WINDOW, "180", 'input[placeholder="180"]']
        ];
        it.each(cases)("saves an empty string instead of 'NaN' for the %s", async (_name, key, initial, selector) => {
          systemService.systemConfig.set({ [key]: initial });
          await flush();
          expect(query(selector).value).toBe(initial);

          await typeInto(selector, "");
          await component.save();

          expect(savedPayload()[key]).toBe("");
        });

        it("saves the number that was typed as a string", async () => {
          await typeInto('input[placeholder="180"]', "240");
          await component.save();
          expect(savedPayload()[TOTP_TIME_WINDOW]).toBe("240");
        });
      });
    });

    describe("after a save", () => {
      it("clears the touched state of the form", async () => {
        component.configForm.values[TIQR_OCRASUITE]().markAsTouched();

        await component.save();

        expect(component.configForm.values[TIQR_OCRASUITE]().touched()).toBe(false);
      });

      it("keeps the form when the save fails", async () => {
        component.configForm.values[TIQR_OCRASUITE]().markAsTouched();
        systemService.saveSystemConfig.mockReturnValueOnce(
          of(new MockPiResponse<Record<string, "insert" | "update">>({ result: { status: false } }))
        );

        await component.save();

        expect(component.configForm.values[TIQR_OCRASUITE]().touched()).toBe(true);
      });
    });

    describe("question slots", () => {
      const slots = () => component.questionKeys().map((key) => component.formData().values[key]);

      beforeEach(async () => {
        systemService.systemConfig.set({ [QUESTION_NUMBER_OF_ANSWERS]: "1", "question.question.0": "Q0" });
        await flush();
      });

      it("adds an empty slot for each answer that is not covered by a question", async () => {
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("3");
        await flush();

        expect(slots()).toEqual(["Q0", "", ""]);
      });

      it("trims the empty slots when the number of answers is lowered", async () => {
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("3");
        await flush();
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("1");
        await flush();

        expect(slots()).toEqual(["Q0"]);
      });

      it("queues a trimmed question of the backend for deletion", async () => {
        systemService.systemConfig.set({
          [QUESTION_NUMBER_OF_ANSWERS]: "2",
          "question.question.0": "Q0",
          "question.question.1": ""
        });
        await flush();
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("1");
        await flush();

        expect(slots()).toEqual(["Q0"]);
        expect(component.pendingDeletes().has("question.question.1")).toBe(true);
      });

      it("keeps an added empty slot while the number of answers is unchanged", async () => {
        component.addQuestion();
        await flush();

        expect(slots()).toEqual(["Q0", ""]);
      });

      it("keeps a slot the user is filling in", async () => {
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("2");
        await flush();
        component.configForm.values["question.question.1"]().controlValue.set("typed");
        await flush();

        expect(slots()).toEqual(["Q0", "typed"]);
      });

      it("blocks the save while a question slot is empty", async () => {
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("2");
        await flush();

        expect(component.configForm().valid()).toBe(false);
        expect(saveButton().disabled).toBe(true);
        expect(await component.save()).toBe(false);
        expect(systemService.saveSystemConfig).not.toHaveBeenCalled();
      });

      it("shows the error of an empty question after the save was refused", async () => {
        component.configForm.values[QUESTION_NUMBER_OF_ANSWERS]().controlValue.set("2");
        await flush();

        await component.save();
        await flush();

        expect(query("app-questionnaire-config").querySelectorAll("mat-error").length).toBe(1);
      });
    });
  });
});
