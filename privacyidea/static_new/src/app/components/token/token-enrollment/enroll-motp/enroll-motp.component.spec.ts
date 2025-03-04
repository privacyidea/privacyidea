import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollMotpComponent } from './enroll-motp.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollMotpComponent', () => {
  let component: EnrollMotpComponent;
  let fixture: ComponentFixture<EnrollMotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollMotpComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollMotpComponent);
    component = fixture.componentInstance;
    component.generateOnServer = signal(false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
