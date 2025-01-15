import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenLayoutComponent} from './token-layout.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

describe('TokenGridComponent', () => {
  let component: TokenLayoutComponent;
  let fixture: ComponentFixture<TokenLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenLayoutComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenLayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
