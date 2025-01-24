import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenEnrollmentComponent} from './token-enrollment.component';

describe('TokenEnrollmentComponent', () => {
  let component: TokenEnrollmentComponent;
  let fixture: ComponentFixture<TokenEnrollmentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
