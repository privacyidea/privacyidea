import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TokenGetSerial } from './token-get-serial.component';

describe('TokenGetSerial', () => {
  let component: TokenGetSerial;
  let fixture: ComponentFixture<TokenGetSerial>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGetSerial, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerial);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
