import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';

import { EnrollYubikeyComponent } from './enroll-yubikey.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import {
  TokenService,
  BasicEnrollmentOptions,
  EnrollmentResponse,
} from '../../../../services/token/token.service';
import { of } from 'rxjs';
import { FormControl } from '@angular/forms';

class MockTokenService {
  tokenTypeOptions = () => [{ key: 'yubikey', text: 'YubiKey Token' }];
  enrollToken = jasmine
    .createSpy('enrollToken')
    .and.returnValue(of({} as EnrollmentResponse));
}

describe('EnrollYubikeyComponent', () => {
  let component: EnrollYubikeyComponent;
  let fixture: ComponentFixture<EnrollYubikeyComponent>;
  let mockTokenService: MockTokenService;

  beforeEach(async () => {
    mockTokenService = new MockTokenService();
    await TestBed.configureTestingModule({
      imports: [EnrollYubikeyComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: mockTokenService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollYubikeyComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit form controls on init', (done) => {
    component.aditionalFormFieldsChange.subscribe((controls) => {
      expect(controls['testYubiKey']).toBeInstanceOf(FormControl);
      expect(controls['otpKey']).toBeInstanceOf(FormControl);
      expect(controls['otpLength']).toBeInstanceOf(FormControl);
      done();
    });
    component.ngOnInit();
  });

  it('should emit clickEnroll function on init', (done) => {
    component.clickEnrollChange.subscribe((func) => {
      expect(func).toBeInstanceOf(Function);
      done();
    });
    component.ngOnInit();
  });

  it('onClickEnroll should call tokenService.enrollToken with correct data when form is valid', () => {
    const basicOptions: BasicEnrollmentOptions = {
      type: 'yubikey',
      description: 'test',
      user: 'u',
      pin: 'p',
    };
    component.otpKeyControl.setValue('12345678901234567890123456789012'); // 32 chars
    component.otpLengthControl.setValue(44);

    component.onClickEnroll(basicOptions);

    expect(mockTokenService.enrollToken).toHaveBeenCalledWith(
      jasmine.objectContaining({
        ...basicOptions,
        type: 'yubikey',
        otpKey: '12345678901234567890123456789012',
        otpLength: 44,
      }),
    );
  });

  it('onClickEnroll should not call tokenService.enrollToken if form is invalid', () => {
    const basicOptions: BasicEnrollmentOptions = {
      type: 'yubikey',
      description: 'test',
      user: 'u',
      pin: 'p',
    };
    component.otpKeyControl.setValue('short'); // Invalid
    component.otpLengthControl.setValue(null); // Invalid

    const result = component.onClickEnroll(basicOptions);

    expect(result).toBeUndefined();
    expect(mockTokenService.enrollToken).not.toHaveBeenCalled();
    expect(component.yubikeyForm.touched).toBeTrue();
  });

  it('should update otpLengthControl when testYubiKeyControl changes', fakeAsync(() => {
    component.testYubiKeyControl.setValue(
      'vvcccccccccccccccccccccccccccccccccccccccc',
    ); // 44 chars
    tick();
    expect(component.otpLengthControl.value).toBe(44);
  }));
});
