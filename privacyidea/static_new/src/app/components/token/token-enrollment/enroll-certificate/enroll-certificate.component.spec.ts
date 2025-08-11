import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollCertificateComponent } from './enroll-certificate.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollCertComponent', () => {
  let component: EnrollCertificateComponent;
  let fixture: ComponentFixture<EnrollCertificateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollCertificateComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollCertificateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
