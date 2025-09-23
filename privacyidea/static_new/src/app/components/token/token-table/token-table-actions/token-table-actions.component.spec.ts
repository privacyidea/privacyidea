import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenTableActionsComponent } from './token-table-actions.component';

describe('TokenTableActionsComponent', () => {
  let component: TokenTableActionsComponent;
  let fixture: ComponentFixture<TokenTableActionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTableActionsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TokenTableActionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
