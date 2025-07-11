import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollTotpComponent } from './enroll-totp.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollTotpComponent', () => {
  let component: EnrollTotpComponent;
  let fixture: ComponentFixture<EnrollTotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTotpComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.generateOnServer = signal(true);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
