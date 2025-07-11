import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollSpassComponent } from './enroll-spass.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import {
  TokenService,
  BasicEnrollmentOptions,
  EnrollmentResponse,
} from '../../../../services/token/token.service';
import { of } from 'rxjs';

class MockTokenService {
  tokenTypeOptions = () => [{ key: 'spass', text: 'SPASS Token' }];
  enrollToken = jasmine
    .createSpy('enrollToken')
    .and.returnValue(of({} as EnrollmentResponse));
}

describe('EnrollSpassComponent', () => {
  let component: EnrollSpassComponent;
  let fixture: ComponentFixture<EnrollSpassComponent>;
  let mockTokenService: MockTokenService;

  beforeEach(async () => {
    mockTokenService = new MockTokenService();
    await TestBed.configureTestingModule({
      imports: [EnrollSpassComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: mockTokenService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSpassComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit empty form controls object on init', (done) => {
    component.aditionalFormFieldsChange.subscribe((controls) => {
      expect(Object.keys(controls).length).toBe(0);
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

  it('onClickEnroll should call tokenService.enrollToken with correct data', () => {
    const basicOptions: BasicEnrollmentOptions = {
      type: 'spass',
      description: 'test',
      user: 'u',
      pin: 'p',
    };
    component.onClickEnroll(basicOptions);
    expect(mockTokenService.enrollToken).toHaveBeenCalledWith(
      jasmine.objectContaining({ ...basicOptions, type: 'spass' }),
    );
  });
});
