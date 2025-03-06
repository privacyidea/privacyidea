import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollPasskeyComponent } from './enroll-passkey.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollPasskeyComponent', () => {
  let component: EnrollPasskeyComponent;
  let fixture: ComponentFixture<EnrollPasskeyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPasskeyComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPasskeyComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
