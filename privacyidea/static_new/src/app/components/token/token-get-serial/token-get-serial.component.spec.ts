import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TokenGetSerial } from './token-get-serial.component';
import { HttpClient, HttpHandler, HttpParams } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { TokenService } from '../../../services/token/token.service';

describe('TokenGetSerial', () => {
  let component: TokenGetSerial;
  let fixture: ComponentFixture<TokenGetSerial>;

  it('should create', async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGetSerial, BrowserAnimationsModule],
      providers: [HttpHandler, HttpClient],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerial);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('get serial with under 100 tokens', async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGetSerial, BrowserAnimationsModule],
      providers: [
        HttpHandler,
        { provide: TokenService, useClass: MockTokenService1 },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerial);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.otpValue.set('123456');
    expect(component.currentStep()).toBe('init');
    component.onPressEnter();
    expect(component.currentStep()).toBe('found');
    expect(component.tokenCount()).toBe('42');
    expect(component.foundSerial()).toBe('OAUTH0001A2B');
  });

  it('get serial with under over 100 tokens', async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGetSerial, BrowserAnimationsModule],
      providers: [
        HttpHandler,
        { provide: TokenService, useClass: MockTokenService2 },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerial);
    component = fixture.componentInstance;
    fixture.detectChanges();
    component.otpValue.set('123456');
    expect(component.currentStep()).toBe('init');
    component.onPressEnter();
    expect(component.currentStep()).toBe('countDone');
    expect(component.tokenCount()).toBe('9001');
    expect(component.foundSerial()).toBe('');
    component.findSerial();
    expect(component.currentStep()).toBe('found');
    expect(component.foundSerial()).toBe('OAUTH0001A2B');
  });
});

class MockTokenService1 {
  getSerial(otp: string, params: HttpParams): Observable<any> {
    if (otp.length === 0) {
      return throwError(() => null);
    }
    if (params.has('count')) {
      return of({
        result: { status: true, value: { count: '42', serial: null } },
      });
    }
    return of({
      result: { status: true, value: { count: null, serial: 'OAUTH0001A2B' } },
    });
  }
}

class MockTokenService2 {
  getSerial(otp: string, params: HttpParams): Observable<any> {
    if (otp.length === 0) {
      return throwError(() => null);
    }
    if (params.has('count')) {
      return of({
        result: { status: true, value: { count: '9001', serial: null } },
      });
    }
    return of({
      result: { status: true, value: { count: '1', serial: 'OAUTH0001A2B' } },
    });
  }
}
