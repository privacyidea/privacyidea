import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenDetailsUserComponent} from './token-details-user.component';

describe('TokenDetailsUserComponent', () => {
  let component: TokenDetailsUserComponent;
  let fixture: ComponentFixture<TokenDetailsUserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsUserComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenDetailsUserComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
