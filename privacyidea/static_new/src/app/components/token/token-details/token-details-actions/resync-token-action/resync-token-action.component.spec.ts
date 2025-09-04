import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ResyncTokenActionComponent } from "./resync-token-action.component";
import { TokenService } from "../../../../../services/token/token.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockTokenService } from "../../../../../../testing/mock-services";


describe("ResyncTokenActionComponent", () => {
  let component: ResyncTokenActionComponent;
  let fixture: ComponentFixture<ResyncTokenActionComponent>;
  let tokenService: TokenService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ResyncTokenActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    })
      .compileComponents();

    tokenService = TestBed.inject(TokenService);
    tokenService.tokenSerial.set("Mock serial");
    fixture = TestBed.createComponent(ResyncTokenActionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should resync OTP token", () => {
    component.fristOTPValue = "otp1";
    component.secondOTPValue = "otp2";

    const resyncSpy = jest.spyOn(tokenService, "resyncOTPToken");
    component.resyncOTPToken();

    expect(resyncSpy).toHaveBeenCalledWith("Mock serial", "otp1", "otp2");
  });

  it("should resync OTP token on button click", () => {
    component.fristOTPValue = "otp1";
    component.secondOTPValue = "otp2";

    const resyncSpy = jest.spyOn(tokenService, "resyncOTPToken");

    const btn: HTMLButtonElement = fixture.nativeElement.querySelector(
      ".actions-pin-input-button button"
    );
    btn.click();

    expect(resyncSpy).toHaveBeenCalledWith("Mock serial", "otp1", "otp2");
  });
});
