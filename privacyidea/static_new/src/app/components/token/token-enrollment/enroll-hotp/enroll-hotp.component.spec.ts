import {ComponentFixture, TestBed} from '@angular/core/testing';

import {EnrollHotpComponent} from './enroll-hotp.component';

describe('EnrollHotpComponent', () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollHotpComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
