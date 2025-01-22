import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenCardComponent} from './token-card.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {signal} from '@angular/core';

describe('TokenCardComponent', () => {
  let component: TokenCardComponent;
  let fixture: ComponentFixture<TokenCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenCardComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenCardComponent);
    component = fixture.componentInstance;
    component.selectedTabIndex = signal(0);
    component.selectedContent = signal('token_overview');
    component.tokenSerial = signal('Mock serial');
    component.revoked = signal(false);
    component.active = signal(true);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
