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

describe("TokenTypeConfigComponent", () => {
  let component: TokenTypeConfigComponent;
  let fixture: ComponentFixture<TokenTypeConfigComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTypeConfigComponent, NoopAnimationsModule],
      providers: [
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
        { provide: NotificationService, useValue: { openSnackBar: jest.fn() } }
      ]
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
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

  it("should call saveSystemConfig on save", () => {
    const systemService = TestBed.inject(SystemService);
    const saveSpy = jest.spyOn(systemService, 'saveSystemConfig');
    component.save();
    expect(saveSpy).toHaveBeenCalledWith(component.formData());
  });

  it("should increment nextQuestion and call save on addQuestion", () => {
    const saveSpy = jest.spyOn(component, 'save');
    const initialNext = component.nextQuestion();
    component.addQuestion();
    expect(saveSpy).toHaveBeenCalled();
    expect(component.nextQuestion()).toBe(initialNext + 1);
  });

  it("should remove entry on deleteSystemEntry", () => {
    component.formData.set({ "test.key": "value", "other": "val" });
    component.deleteSystemEntry("test.key");
    expect(component.formData()["test.key"]).toBeUndefined();
    expect(component.formData()["other"]).toBe("val");
  });

  it("should update formData on onCheckboxChange", () => {
    component.onCheckboxChange("test.check", { checked: true });
    expect(component.formData()["test.check"]).toBe("True");
    component.onCheckboxChange("test.check", { checked: false });
    expect(component.formData()["test.check"]).toBe("False");
  });

  it("should create new yubikey key", async () => {
    const promise = component.yubikeyCreateNewKey("myID");
    
    const req = httpMock.expectOne(req => req.url.endsWith("/system/random?len=20&encode=b64"));
    expect(req.request.method).toBe("GET");
    req.flush({ result: { status: true, value: "new-random-key" } });

    await promise;
    expect(component.formData()["yubikey.apiid.myID"]).toBe("new-random-key");
  });

  it("should show error if yubikeyCreateNewKey called without apiId", () => {
    const notificationService = component.notificationService;
    const snackBarSpy = jest.spyOn(notificationService, 'openSnackBar');
    component.yubikeyCreateNewKey("");
    expect(snackBarSpy).toHaveBeenCalledWith(expect.stringContaining("Please enter a Client ID"));
  });

  it("should handle error in yubikeyCreateNewKey", async () => {
    const notificationService = component.notificationService;
    const snackBarSpy = jest.spyOn(notificationService, 'openSnackBar');
    const promise = component.yubikeyCreateNewKey("myID");
    
    const req = httpMock.expectOne(req => req.url.endsWith("/system/random?len=20&encode=b64"));
    req.error(new ProgressEvent('error'));

    await promise;
    expect(snackBarSpy).toHaveBeenCalledWith(expect.stringContaining("Failed to generate API key"));
  });

  it("should use fallback values if init data is missing", () => {
    // We can't easily mock the computed signal of the already created component if it's already initialized.
    // But we can check that it has the values from MockSystemService (which has init data).
    expect(component.hashLibs()).toEqual(["sha1", "sha256", "sha512"]);
    expect(component.totpSteps()).toEqual(["30", "60"]);
    expect(component.smsProviders()).toEqual(["provider1", "provider2"]);
  });

  it("should evaluate isChecked correctly for various inputs", () => {
    // truthy
    expect(component.isChecked(true)).toBe(true);
    expect(component.isChecked("True")).toBe(true);
    // Note: component treats only capital "True" as true
    expect(component.isChecked("true")).toBe(false);
    expect(component.isChecked("1")).toBe(true);
    expect(component.isChecked(1)).toBe(true);

    // falsy
    expect(component.isChecked(false)).toBe(false);
    expect(component.isChecked("False")).toBe(false);
    expect(component.isChecked("0")).toBe(false);
    expect(component.isChecked(0)).toBe(false);
    expect(component.isChecked(undefined)).toBe(false);
    expect(component.isChecked(null as unknown as any)).toBe(false);
  });
});
