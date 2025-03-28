import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollQuestionComponent } from './enroll-question.component';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollQuestionnaireComponent', () => {
  let component: EnrollQuestionComponent;
  let fixture: ComponentFixture<EnrollQuestionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollQuestionComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollQuestionComponent);
    component = fixture.componentInstance;
    component.answers = signal({});
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
