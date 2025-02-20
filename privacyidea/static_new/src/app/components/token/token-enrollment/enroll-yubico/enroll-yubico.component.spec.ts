import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollYubicoComponent } from './enroll-yubico.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollYubicoComponent', () => {
  let component: EnrollYubicoComponent;
  let fixture: ComponentFixture<EnrollYubicoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollYubicoComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollYubicoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
