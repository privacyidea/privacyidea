import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollAspComponent } from './enroll-asp.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollAspComponent', () => {
  let component: EnrollAspComponent;
  let fixture: ComponentFixture<EnrollAspComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollAspComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollAspComponent);
    component = fixture.componentInstance;
    component.generateOnServer = signal(false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
