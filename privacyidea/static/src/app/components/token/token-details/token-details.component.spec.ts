import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenDetailsComponent } from './token-details.component';

describe('TokenDetailsComponent', () => {
  let component: TokenDetailsComponent;
  let fixture: ComponentFixture<TokenDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
