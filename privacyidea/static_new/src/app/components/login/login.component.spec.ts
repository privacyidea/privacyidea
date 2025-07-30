import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { LoginComponent } from './login.component';
import { AuthService } from '../../services/auth/auth.service';
import { LocalService } from '../../services/local/local.service';
import { NotificationService } from '../../services/notification/notification.service';
import { SessionTimerService } from '../../services/session-timer/session-timer.service';

describe('LoginComponent (Jest)', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;

  const authService = {
    isAuthenticatedUser: jest.fn().mockReturnValue(false),
    authenticate: jest.fn().mockReturnValue(of({})),
    deauthenticate: jest.fn(),
  } as unknown as jest.Mocked<AuthService>;

  const localService = {
    bearerTokenKey: 'bearerTokenKey',
    saveData: jest.fn(),
    removeData: jest.fn(),
  } as unknown as jest.Mocked<LocalService>;

  const notificationService = {
    openSnackBar: jest.fn(),
  } as unknown as jest.Mocked<NotificationService>;

  const sessionTimerService = {
    startRefreshingRemainingTime: jest.fn(),
    startTimer: jest.fn(),
  } as unknown as jest.Mocked<SessionTimerService>;

  const router = {
    navigateByUrl: jest.fn().mockResolvedValue(true),
    navigate: jest.fn().mockResolvedValue(true),
  } as unknown as jest.Mocked<Router>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LoginComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: LocalService, useValue: localService },
        { provide: NotificationService, useValue: notificationService },
        { provide: SessionTimerService, useValue: sessionTimerService },
        { provide: Router, useValue: router },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should warn and open a snack bar if the user is already logged in', () => {
    authService.isAuthenticatedUser.mockReturnValue(true);
    const warn = jest.spyOn(console, 'warn').mockImplementation();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      'User is already logged in.',
    );
    expect(warn).toHaveBeenCalledWith('User is already logged in.');

    warn.mockRestore();
  });

  describe('onSubmit', () => {
    beforeEach(() => {
      component.username.set('test-user');
      component.password.set('test-pass');
    });

    it('should call authService.authenticate with username/password', () => {
      authService.isAuthenticatedUser.mockReturnValue(true);

      component.onSubmit();

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: 'test-user',
        password: 'test-pass',
      });
    });

    it('should handle successful login', () => {
      authService.authenticate.mockReturnValue(
        of({ result: { value: { token: 'fake-token' } } } as any),
      );
      authService.isAuthenticatedUser.mockReturnValue(true);

      component.onSubmit();

      expect(localService.saveData).toHaveBeenCalledWith(
        localService.bearerTokenKey,
        'fake-token',
      );
      expect(
        sessionTimerService.startRefreshingRemainingTime,
      ).toHaveBeenCalled();
      expect(sessionTimerService.startTimer).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith('/tokens');
    });

    it('should handle missing or invalid token (challenge response)', () => {
      authService.authenticate.mockReturnValue(of({ result: {} }) as any);

      component.onSubmit();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        'Login failed. Challenge response required.',
      );
      expect(localService.saveData).not.toHaveBeenCalled();
      expect(
        sessionTimerService.startRefreshingRemainingTime,
      ).not.toHaveBeenCalled();
      expect(sessionTimerService.startTimer).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('logout', () => {
    it('should remove token, deauthenticate, and navigate to login', async () => {
      component.logout();

      expect(localService.removeData).toHaveBeenCalledWith(
        localService.bearerTokenKey,
      );
      expect(authService.deauthenticate).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['login']);
    });
  });
});
