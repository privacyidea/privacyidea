import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollVascoComponent } from './enroll-vasco.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollVascoComponent', () => {
  let component: EnrollVascoComponent;
  let fixture: ComponentFixture<EnrollVascoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollVascoComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollVascoComponent);
    component = fixture.componentInstance;
    component.useVascoSerial = signal(true);
    component.vascoSerial = signal('');
    component.otpKey = signal('');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
