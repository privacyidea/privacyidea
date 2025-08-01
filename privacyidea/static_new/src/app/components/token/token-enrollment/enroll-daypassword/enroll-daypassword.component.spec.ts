import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollDaypasswordComponent } from './enroll-daypassword.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollDaypasswordComponent', () => {
  let component: EnrollDaypasswordComponent;
  let fixture: ComponentFixture<EnrollDaypasswordComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollDaypasswordComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
