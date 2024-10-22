import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenGridComponent } from './token-grid.component';

describe('TokenGridComponent', () => {
  let component: TokenGridComponent;
  let fixture: ComponentFixture<TokenGridComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGridComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TokenGridComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
