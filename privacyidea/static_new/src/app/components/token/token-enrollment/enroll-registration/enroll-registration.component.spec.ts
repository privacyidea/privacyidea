import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollRegistrationComponent } from './enroll-registration.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollRegistrationComponent', () => {
  let component: EnrollRegistrationComponent;
  let fixture: ComponentFixture<EnrollRegistrationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRegistrationComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollRegistrationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
