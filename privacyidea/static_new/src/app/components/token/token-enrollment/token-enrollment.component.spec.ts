import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenEnrollmentComponent } from './token-enrollment.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';

describe('TokenEnrollmentComponent', () => {
  let component: TokenEnrollmentComponent;
  let fixture: ComponentFixture<TokenEnrollmentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock container serial');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
