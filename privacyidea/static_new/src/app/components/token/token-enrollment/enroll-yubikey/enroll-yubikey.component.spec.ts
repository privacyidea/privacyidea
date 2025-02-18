import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollYubikeyComponent } from './enroll-yubikey.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollYubikeyComponent', () => {
  let component: EnrollYubikeyComponent;
  let fixture: ComponentFixture<EnrollYubikeyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollYubikeyComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollYubikeyComponent);
    component = fixture.componentInstance;
    component.otpLength = signal(44);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
