import {ComponentFixture, TestBed} from '@angular/core/testing';

import {TokenIdentifySerialComponent} from './token-get-serial.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

describe('TokenIdentifySerialComponent', () => {
  let component: TokenIdentifySerialComponent;
  let fixture: ComponentFixture<TokenIdentifySerialComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenIdentifySerialComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenIdentifySerialComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
