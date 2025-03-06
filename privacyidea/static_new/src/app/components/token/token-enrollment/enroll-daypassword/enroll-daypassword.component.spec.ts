import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollDaypasswordComponent } from './enroll-daypassword.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';

describe('EnrollDaypasswordComponent', () => {
  let component: EnrollDaypasswordComponent;
  let fixture: ComponentFixture<EnrollDaypasswordComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollDaypasswordComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    component.timeStep = signal('');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
