import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenCardComponent} from './token-card.component';

describe('TokenCardComponent', () => {
  let component: TokenCardComponent;
  let fixture: ComponentFixture<TokenCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenCardComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
