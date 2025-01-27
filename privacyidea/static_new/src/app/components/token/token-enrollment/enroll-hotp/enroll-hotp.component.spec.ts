import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollHotpComponent } from './enroll-hotp.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollHotpComponent', () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollHotpComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    component.generateOnServer = signal(false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
