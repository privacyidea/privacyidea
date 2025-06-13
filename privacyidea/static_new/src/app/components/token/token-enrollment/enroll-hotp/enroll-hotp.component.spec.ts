import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';

import { EnrollHotpComponent } from './enroll-hotp.component';
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
  tokenTypeOptions = () => [{ key: 'hotp', text: 'HOTP Token' }];
  enrollToken = jasmine
    .createSpy('enrollToken')
    .and.returnValue(of({} as EnrollmentResponse));
}

describe('EnrollHotpComponent', () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;
  let mockTokenService: MockTokenService;

  beforeEach(async () => {
    mockTokenService = new MockTokenService();
    await TestBed.configureTestingModule({
      imports: [EnrollHotpComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: mockTokenService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit form controls on init', (done) => {
    component.aditionalFormFieldsChange.subscribe((controls) => {
      expect(controls['generateOnServer']).toBeInstanceOf(FormControl);
      expect(controls['otpLength']).toBeInstanceOf(FormControl);
      expect(controls['otpKey']).toBeInstanceOf(FormControl);
      expect(controls['hashAlgorithm']).toBeInstanceOf(FormControl);
      done();
    });
    component.ngOnInit(); // ngOnInit is called by fixture.detectChanges() initially, direct call for isolated test
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
      type: 'hotp',
      description: 'test',
      user: 'u',
      pin: 'p',
    };
    component.generateOnServerFormControl.setValue(false);
    component.otpKeyFormControl.setValue('1234567890123456'); // Valid key
    component.otpLengthFormControl.setValue(6);
    component.hashAlgorithmFormControl.setValue('sha1');

    component.onClickEnroll(basicOptions);

    expect(mockTokenService.enrollToken).toHaveBeenCalledWith(
      jasmine.objectContaining({
        ...basicOptions,
        type: 'hotp',
        generateOnServer: false,
        otpLength: 6,
        otpKey: '1234567890123456',
        hashAlgorithm: 'sha1',
      }),
    );
  });

  it('onClickEnroll should not call tokenService.enrollToken if form is invalid (e.g., OTP key missing when not generating on server)', () => {
    const basicOptions: BasicEnrollmentOptions = {
      type: 'hotp',
      description: 'test',
      user: 'u',
      pin: 'p',
    };
    component.generateOnServerFormControl.setValue(false);
    component.otpKeyFormControl.setValue(''); // Invalid: OTP key required
    component.otpLengthFormControl.setValue(6);
    component.hashAlgorithmFormControl.setValue('sha1');

    const result = component.onClickEnroll(basicOptions);

    expect(result).toBeUndefined();
    expect(mockTokenService.enrollToken).not.toHaveBeenCalled();
    expect(component.otpKeyFormControl.touched).toBeTrue();
  });

  it('should update otpKeyFormControl validators when generateOnServerFormControl changes', fakeAsync(() => {
    component.generateOnServerFormControl.setValue(true);
    tick();
    expect(component.otpKeyFormControl.validator).toBeNull();

    component.generateOnServerFormControl.setValue(false);
    tick();
    expect(component.otpKeyFormControl.validator).not.toBeNull();
    component.otpKeyFormControl.setValue('');
    expect(component.otpKeyFormControl.valid).toBeFalse();
  }));
});
