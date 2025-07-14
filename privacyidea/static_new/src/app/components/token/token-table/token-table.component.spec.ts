import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { TokenTableComponent } from './token-table.component';

describe('TokenTableComponent', () => {
  let component: TokenTableComponent;
  let fixture: ComponentFixture<TokenTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient()],
      imports: [TokenTableComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
