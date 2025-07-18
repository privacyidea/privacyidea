import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollQuestionComponent } from './enroll-question.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollQuestionnaireComponent', () => {
  let component: EnrollQuestionComponent;
  let fixture: ComponentFixture<EnrollQuestionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollQuestionComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollQuestionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
