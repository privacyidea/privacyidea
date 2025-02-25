import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollTanComponent } from './enroll-tan.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollTanComponent', () => {
  let component: EnrollTanComponent;
  let fixture: ComponentFixture<EnrollTanComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTanComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTanComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
