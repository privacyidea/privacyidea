import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenGridComponent} from './token-grid.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

describe('TokenGridComponent', () => {
  let component: TokenGridComponent;
  let fixture: ComponentFixture<TokenGridComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGridComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
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
