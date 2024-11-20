import {ComponentFixture, TestBed} from '@angular/core/testing';
import {provideHttpClientTesting} from '@angular/common/http/testing'; // Import this
import {TokenDetailsComponent} from './token-details.component';
import {provideHttpClient} from '@angular/common/http';
import {signal} from '@angular/core';

describe('TokenDetailsComponent', () => {
  let component: TokenDetailsComponent;
  let fixture: ComponentFixture<TokenDetailsComponent>;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TokenDetailsComponent
      ],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    component.serial = signal('Mock serial');

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
