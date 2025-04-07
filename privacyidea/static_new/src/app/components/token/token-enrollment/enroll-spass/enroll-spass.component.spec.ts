import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollSpassComponent } from './enroll-spass.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollSpassComponent', () => {
  let component: EnrollSpassComponent;
  let fixture: ComponentFixture<EnrollSpassComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSpassComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSpassComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
