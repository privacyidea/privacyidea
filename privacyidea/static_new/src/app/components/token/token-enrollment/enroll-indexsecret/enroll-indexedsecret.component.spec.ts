import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollIndexedsecretComponent } from './enroll-indexedsecret.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollIndexsecretComponent', () => {
  let component: EnrollIndexedsecretComponent;
  let fixture: ComponentFixture<EnrollIndexedsecretComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollIndexedsecretComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollIndexedsecretComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
