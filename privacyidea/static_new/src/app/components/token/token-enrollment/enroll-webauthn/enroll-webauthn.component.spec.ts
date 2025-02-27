import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollWebauthnComponent } from './enroll-webauthn.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollWebauthnComponent', () => {
  let component: EnrollWebauthnComponent;
  let fixture: ComponentFixture<EnrollWebauthnComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollWebauthnComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollWebauthnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
