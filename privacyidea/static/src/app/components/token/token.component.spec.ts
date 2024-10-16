import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenComponent } from './token.component';

describe('TokenComponent', () => {
  let component: TokenComponent;
  let fixture: ComponentFixture<TokenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TokenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
