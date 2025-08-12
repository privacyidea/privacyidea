import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TestOtpPinActionComponent } from './test-otp-pin-action.component';

describe('TestOtpPinActionComponent', () => {
  let component: TestOtpPinActionComponent;
  let fixture: ComponentFixture<TestOtpPinActionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestOtpPinActionComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TestOtpPinActionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
