import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenDetailsActionsComponent } from './token-details-actions.component';
import { TokenService } from '../../../../services/token/token.service';
import { ValidateService } from '../../../../services/validate/validate.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { signal } from '@angular/core';

class MockTokenService {
  resyncOTPToken() {
    return of(null);
  }
  testToken() {
    return of(null);
  }
}

describe('TokenDetailsActionsComponent', () => {
  let component: TokenDetailsActionsComponent;
  let fixture: ComponentFixture<TokenDetailsActionsComponent>;
  let tokenService: TokenService;
  let validateService: ValidateService;

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        ValidateService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsActionsComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal('Mock serial');
    component.refreshTokenDetails = signal(false);
    component.tokenType = signal('Mock type');

    tokenService = TestBed.inject(TokenService);
    validateService = TestBed.inject(ValidateService);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should test and verify token', () => {
    const testSpy = jest.spyOn(validateService, 'testToken');
    component.otpOrPinToTest = '1234';

    component.testToken();
    component.verifyOTPValue();

    expect(testSpy).toHaveBeenCalledWith('Mock serial', '1234');
  });

  it('should resync OTP token', () => {
    component.fristOTPValue = 'otp1';
    component.secondOTPValue = 'otp2';

    const resyncSpy = jest.spyOn(tokenService, 'resyncOTPToken');
    component.resyncOTPToken();

    expect(resyncSpy).toHaveBeenCalledWith('Mock serial', 'otp1', 'otp2');
  });

  it('should resync OTP token on button click', () => {
    component.fristOTPValue = 'otp1';
    component.secondOTPValue = 'otp2';

    const resyncSpy = jest.spyOn(tokenService, 'resyncOTPToken');

    const btn: HTMLButtonElement = fixture.nativeElement.querySelector(
      '.actions-pin-input-button button',
    );
    btn.click();

    expect(resyncSpy).toHaveBeenCalledWith('Mock serial', 'otp1', 'otp2');
  });
});
