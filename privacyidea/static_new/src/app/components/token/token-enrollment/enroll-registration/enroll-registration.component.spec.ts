import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollRegistrationComponent } from './enroll-registration.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollRegistrationComponent', () => {
  let component: EnrollRegistrationComponent;
  let fixture: ComponentFixture<EnrollRegistrationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRegistrationComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollRegistrationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
