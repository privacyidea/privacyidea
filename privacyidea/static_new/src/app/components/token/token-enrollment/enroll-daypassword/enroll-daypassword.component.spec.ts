import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollDaypasswordComponent } from './enroll-daypassword.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollDaypasswordComponent', () => {
  let component: EnrollDaypasswordComponent;
  let fixture: ComponentFixture<EnrollDaypasswordComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollDaypasswordComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
