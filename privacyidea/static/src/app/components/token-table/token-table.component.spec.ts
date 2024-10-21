import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenTableComponent } from './token-table.component';

describe('TokenComponent', () => {
  let component: TokenTableComponent;
  let fixture: ComponentFixture<TokenTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTableComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
