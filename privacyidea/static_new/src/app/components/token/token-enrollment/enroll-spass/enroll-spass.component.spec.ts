import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollSpassComponent } from './enroll-spass.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollSpassComponent', () => {
  let component: EnrollSpassComponent;
  let fixture: ComponentFixture<EnrollSpassComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSpassComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSpassComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
