import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollFoureyesComponent } from './enroll-foureyes.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollFoureyesComponent', () => {
  let component: EnrollFoureyesComponent;
  let fixture: ComponentFixture<EnrollFoureyesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollFoureyesComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollFoureyesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
