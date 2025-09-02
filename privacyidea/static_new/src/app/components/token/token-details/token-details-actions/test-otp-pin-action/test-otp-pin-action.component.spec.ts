import { ComponentFixture, TestBed } from "@angular/core/testing";

import { TestOtpPinActionComponent } from "./test-otp-pin-action.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ValidateService } from "../../../../../services/validate/validate.service";
import { TokenService } from "../../../../../services/token/token.service";
import { MockTokenService } from "../../../../../../testing/mock-services";

describe("TestOtpPinActionComponent", () => {
  let component: TestOtpPinActionComponent;
  let fixture: ComponentFixture<TestOtpPinActionComponent>;
  let validateService: ValidateService;
  let tokenService: TokenService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TestOtpPinActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TestOtpPinActionComponent);
    component = fixture.componentInstance;
    validateService = TestBed.inject(ValidateService);
    tokenService = TestBed.inject(TokenService);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should test and verify token", () => {
    const testSpy = jest.spyOn(validateService, "testToken");
    component.otpOrPinToTest = "1234";
    tokenService.tokenSerial.set("Mock serial");

    component.testToken();
    component.verifyOTPValue();

    expect(testSpy).toHaveBeenCalledWith("Mock serial", "1234");
  });
});
