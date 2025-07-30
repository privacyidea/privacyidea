import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollApplspecComponent } from './enroll-applspec.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollAspComponent', () => {
  let component: EnrollApplspecComponent;
  let fixture: ComponentFixture<EnrollApplspecComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollApplspecComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollApplspecComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
