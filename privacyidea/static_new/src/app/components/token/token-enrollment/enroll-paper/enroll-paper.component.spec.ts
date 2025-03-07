import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollPaperComponent } from './enroll-paper.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollPaperComponent', () => {
  let component: EnrollPaperComponent;
  let fixture: ComponentFixture<EnrollPaperComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPaperComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPaperComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
