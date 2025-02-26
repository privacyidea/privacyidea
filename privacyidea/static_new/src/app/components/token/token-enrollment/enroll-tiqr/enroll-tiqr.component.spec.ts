import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollTiqrComponent } from './enroll-tiqr.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollTiqrComponent', () => {
  let component: EnrollTiqrComponent;
  let fixture: ComponentFixture<EnrollTiqrComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTiqrComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTiqrComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
