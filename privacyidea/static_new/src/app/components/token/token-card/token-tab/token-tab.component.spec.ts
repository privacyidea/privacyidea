import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenTabComponent} from './token-tab.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {signal} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

describe('TokenTabComponent', () => {
  let component: TokenTabComponent;
  let fixture: ComponentFixture<TokenTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTabComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenTabComponent);
    component = fixture.componentInstance;
    component.tokenIsSelected = signal(false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
