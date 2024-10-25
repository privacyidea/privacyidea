import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenTabComponent} from './token-tab.component';

describe('TokenTabComponent', () => {
  let component: TokenTabComponent;
  let fixture: ComponentFixture<TokenTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTabComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
