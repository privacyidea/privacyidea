import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginComponent } from './login.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AuthService } from '../../services/auth/auth.service';
import { LocalService } from '../../services/local/local.service';
import { NotificationService } from '../../services/notification/notification.service';
import { SessionTimerService } from '../../services/session-timer/session-timer.service';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let authService: AuthService;
  let localService: LocalService;
  let notificationService: NotificationService;
  let sessionTimerService: SessionTimerService;
  let router: Router;

  const mockAuthService = {
    isAuthenticatedUser() {
      return false;
    },
    authenticate(_username: string, _password: string) {
      return of({});
    },
    deauthenticate() {},
  };

  const mockLocalService = {
    bearerTokenKey: 'bearerTokenKey',
    saveData(_key: string, _data: string) {},
    removeData(_key: string) {},
  };

  const mockNotificationService = {
    openSnackBar(_message: string) {},
  };

  const mockSessionTimerService = {
    startRefreshingRemainingTime() {},
    startTimer() {},
  };

  const mockRouter = {
    navigate(_commands: any[]) {
      return Promise.resolve(true);
    },
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
        { provide: LocalService, useValue: mockLocalService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: SessionTimerService, useValue: mockSessionTimerService },
        { provide: Router, useValue: mockRouter },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;

    authService = TestBed.inject(AuthService);
    localService = TestBed.inject(LocalService);
    notificationService = TestBed.inject(NotificationService);
    sessionTimerService = TestBed.inject(SessionTimerService);
    router = TestBed.inject(Router);
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should warn and open a snack bar if the user is already logged in', () => {
    spyOn(authService, 'isAuthenticatedUser').and.returnValue(true);
    spyOn(notificationService, 'openSnackBar').and.callThrough();
    spyOn(console, 'warn');

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      'User is already logged in.',
    );
    expect(console.warn).toHaveBeenCalledWith('User is already logged in.');
  });

  describe('onSubmit', () => {
    beforeEach(() => {
      spyOn(authService, 'authenticate').and.callThrough();
      spyOn(authService, 'isAuthenticatedUser').and.callThrough();
      spyOn(localService, 'saveData').and.callThrough();
      spyOn(notificationService, 'openSnackBar').and.callThrough();
      spyOn(
        sessionTimerService,
        'startRefreshingRemainingTime',
      ).and.callThrough();
      spyOn(sessionTimerService, 'startTimer').and.callThrough();
      spyOn(router, 'navigate').and.callThrough();

      component.username.set('test-user');
      component.password.set('test-pass');
    });

    it('should call authService.authenticate with username/password signals', () => {
      authService.isAuthenticatedUser = jasmine
        .createSpy()
        .and.returnValue(true);

      component.onSubmit();

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: 'test-user',
        password: 'test-pass',
      });
    });

    it('should handle successful login', () => {
      (authService.authenticate as jasmine.Spy).and.returnValue(
        of({ result: { value: { token: 'fake-token' } } }),
      );
      (authService.isAuthenticatedUser as jasmine.Spy).and.returnValue(true);

      component.onSubmit();

      expect(localService.saveData).toHaveBeenCalledWith(
        localService.bearerTokenKey,
        'fake-token',
      );
      expect(
        sessionTimerService.startRefreshingRemainingTime,
      ).toHaveBeenCalled();
      expect(sessionTimerService.startTimer).toHaveBeenCalled();
    });

    it('should handle missing or invalid token (trigger challenge response)', () => {
      (authService.authenticate as jasmine.Spy).and.returnValue(
        of({ result: {} }),
      );

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
    it('should call removeData, deauthenticate, and navigate to login', () => {
      spyOn(localService, 'removeData').and.callThrough();
      spyOn(authService, 'deauthenticate').and.callThrough();
      spyOn(router, 'navigate').and.callThrough();

      component.logout();

      expect(localService.removeData).toHaveBeenCalledWith(
        localService.bearerTokenKey,
      );
      expect(authService.deauthenticate).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['login']);
    });
  });
});
