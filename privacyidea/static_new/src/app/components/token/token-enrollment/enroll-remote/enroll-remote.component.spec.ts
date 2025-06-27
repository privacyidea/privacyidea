import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollRemoteComponent } from './enroll-remote.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollRemoteComponent', () => {
  let component: EnrollRemoteComponent;
  let fixture: ComponentFixture<EnrollRemoteComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRemoteComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollRemoteComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
