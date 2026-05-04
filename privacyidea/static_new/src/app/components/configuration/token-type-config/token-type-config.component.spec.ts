import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TokenTypeConfigComponent } from "./token-type-config.component";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { SystemService } from "../../../services/system/system.service";
import { SmsGatewayService } from "../../../services/sms-gateway/sms-gateway.service";
import { SmtpService } from "../../../services/smtp/smtp.service";
import { MockSystemService } from "../../../../testing/mock-services";
import { signal } from "@angular/core";
import { NotificationService } from "../../../services/notification/notification.service";
import { ActivatedRoute } from "@angular/router";
import { Observable, of } from "rxjs";

class MockActivatedRoute {
  fragment: Observable<string | undefined> = of();
  queryParams: Observable<Record<string, any>> = of({});
}

describe("TokenTypeConfigComponent", () => {
  let component: TokenTypeConfigComponent;
  let fixture: ComponentFixture<TokenTypeConfigComponent>;
  let httpMock: HttpTestingController;
  let activatedRoute: MockActivatedRoute;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTypeConfigComponent, NoopAnimationsModule],
      providers: [
        { provide: ActivatedRoute, useClass: MockActivatedRoute },
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        {
          provide: SmsGatewayService,
          useValue: {
            smsGateways: signal([]),
            smsGatewayResource: { value: () => ({ result: { value: [] } }) }
          }
        },
        {
          provide: SmtpService,
          useValue: {
            smtpServers: signal([]),
            smtpServerResource: { value: () => ({ result: { value: {} } }) }
          }
        },
        { provide: NotificationService, useValue: { openSnackBar: jest.fn(), handleResourceError: jest.fn() } }
      ]
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    activatedRoute = TestBed.inject(ActivatedRoute) as unknown as MockActivatedRoute;
    jest.spyOn(document, "getElementById").mockReturnValue({ scrollIntoView: jest.fn() } as any);

    fixture = TestBed.createComponent(TokenTypeConfigComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize formData from systemConfig", () => {
    expect(component.formData()["splitAtSign"]).toBe(true);
    expect(component.formData()["someOtherConfig"]).toBe("test_value");
  });

  it("should calculate questionKeys correctly", () => {
    component.formData.set({
      "question.question.1": "Q1",
      "question.question.2": "Q2",
      "other": "val"
    });
    expect(component.questionKeys).toEqual(["question.question.1", "question.question.2"]);
  });

  it("should calculate yubikeyApiIds correctly", () => {
    component.formData.set({
      "yubikey.apiid.ID1": "KEY1",
      "yubikey.apiid.ID2": "KEY2",
      "other": "val"
    });
    expect(component.yubikeyApiIds).toEqual(["yubikey.apiid.ID1", "yubikey.apiid.ID2"]);
  });

  it("should call saveSystemConfig on save", async () => {
    const systemService = TestBed.inject(SystemService);
    const saveSpy = jest.spyOn(systemService, "saveSystemConfig");
    const reloadSpy = jest.spyOn((systemService as any).systemConfigResource, "reload");

    await component.save();

    expect(saveSpy).toHaveBeenCalledWith(component.formData());
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should add new question to formData and increment nextQuestion without saving", () => {
    const saveSpy = jest.spyOn(component, "save");
    const initialNext = component.nextQuestionIndex();
    const newQuestion = "My new question?";

    component.addQuestion(newQuestion);

    expect(component.formData()[`question.question.${initialNext}`]).toBe(newQuestion);
    expect(component.nextQuestionIndex()).toBe(initialNext + 1);
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it("should update formData and pendingDeletes but not call service on deleteSystemEntry", () => {
    const systemService = TestBed.inject(SystemService);
    const deleteSpy = jest.spyOn(systemService as any, "deleteSystemConfig");
    const reloadSpy = jest.spyOn((systemService as any).systemConfigResource, "reload");

    const entryToDelete = "yubikey.apiid.123";
    const entryToKeep = "yubikey.apiid.456";

    // Set initial config so it's tracked for deferred deletion
    (systemService as any).systemConfig.set({ [entryToDelete]: "123", [entryToKeep]: "456" });
    fixture.detectChanges();

    component.deleteSystemEntry(entryToDelete);

    expect(deleteSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(component.formData()).not.toHaveProperty(entryToDelete);
    expect(component.formData()[entryToKeep]).toEqual("456");
    expect(component.pendingDeletes().has(entryToDelete)).toBe(true);
  });

  it("should update formData on onCheckboxChange", () => {
    component.onCheckboxChange("test.check", { checked: true });
    expect(component.formData()["test.check"]).toBe("True");
    component.onCheckboxChange("test.check", { checked: false });
    expect(component.formData()["test.check"]).toBe("False");
  });

  it("should create new yubikey key", async () => {
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "", generateKey: true });

    const req = httpMock.expectOne(req => req.url.endsWith("/system/random?len=20&encode=b64"));
    expect(req.request.method).toBe("GET");
    req.flush({ result: { status: true, value: "new-random-key" } });

    await promise;
    expect(component.formData()["yubikey.apiid.myID"]).toBe("new-random-key");
  });

  it("should only add, but not generate api key", async () => {
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "123", generateKey: false });

    httpMock.expectNone(req => req.url.endsWith("/system/random?len=20&encode=b64"));

    await promise;
    expect(component.formData()["yubikey.apiid.myID"]).toBe("123");
  });

  it("generateKey wins over apiKey if both are provided", async () => {
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "123", generateKey: true });

    const req = httpMock.expectOne(req => req.url.endsWith("/system/random?len=20&encode=b64"));
    expect(req.request.method).toBe("GET");
    req.flush({ result: { status: true, value: "new-random-key" } });

    await promise;
    expect(component.formData()["yubikey.apiid.myID"]).toBe("new-random-key");
  });

  it("should show error if yubikeyCreateNewKey called without apiId", () => {
    const notificationService = component.notificationService;
    const snackBarSpy = jest.spyOn(notificationService, "openSnackBar");
    component.yubikeyAddNewKey({ apiId: "", apiKey: "", generateKey: true });
    expect(snackBarSpy).toHaveBeenCalledWith(expect.stringContaining("Please enter a Client ID"));
  });

  it("should handle error in yubikeyCreateNewKey", async () => {
    const notificationService = component.notificationService;
    const snackBarSpy = jest.spyOn(notificationService, "openSnackBar");
    const promise = component.yubikeyAddNewKey({ apiId: "myID", apiKey: "", generateKey: true });

    const req = httpMock.expectOne(req => req.url.endsWith("/system/random?len=20&encode=b64"));
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
      jest.spyOn(document, "getElementById").mockReturnValue({ scrollIntoView: scrollSpy } as any);
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

      it("should scroll to referenced panel when expandedPanel is defined", () => {
        const scrollSpy = jest.fn();
        jest.spyOn(document, "getElementById").mockReturnValue({ scrollIntoView: scrollSpy } as any);
        component.ngAfterViewInit();
        expect(scrollSpy).toHaveBeenCalledWith({ behavior: "smooth" });
      });
    });
  });
});
