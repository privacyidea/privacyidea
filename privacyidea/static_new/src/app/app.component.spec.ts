import { fakeAsync, TestBed, tick } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { appConfig } from './app.config';
import { APP_BASE_HREF, Location } from '@angular/common';
import { provideRouter, Router } from '@angular/router';
import { routes } from './app.routes';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AuthGuard } from './guards/auth.guard';

class MockAuthGuard {
  canActivate() {
    return true;
  }
}

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes),
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have the 'privacyidea-webui' title`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.title).toEqual('privacyidea-webui');
  });

  it('should call sessionTimerService methods in constructor if user is authenticated', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    const sessionTimerService = (app as any).sessionTimerService;
    spyOn(sessionTimerService, 'startTimer').and.callThrough();
    spyOn(sessionTimerService, 'resetTimer').and.callThrough();

    const authService = (app as any).authService;
    spyOn(authService, 'isAuthenticatedUser').and.returnValue(true);

    const notificationService = (app as any).notificationService;
    spyOn(notificationService, 'openSnackBar').and.callThrough();

    const newFixture = TestBed.createComponent(AppComponent);
    newFixture.detectChanges();
    expect(sessionTimerService.startTimer).toHaveBeenCalled();
    expect(authService.isAuthenticatedUser).toHaveBeenCalled();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      'User is already logged in.',
    );
  });

  it('should reset and start session timer when user interacts (click, keydown, mousemove, scroll)', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const app = fixture.componentInstance;
    const sessionTimerService = (app as any).sessionTimerService;
    spyOn(sessionTimerService, 'resetTimer');
    spyOn(sessionTimerService, 'startTimer');

    const event = new Event('click');
    document.dispatchEvent(event);

    expect(sessionTimerService.resetTimer).toHaveBeenCalled();
    expect(sessionTimerService.startTimer).toHaveBeenCalled();
  });

  describe('appConfig', () => {
    it('should define providers array', () => {
      expect(appConfig.providers).toBeDefined();
    });

    it('should contain APP_BASE_HREF set to /ui/', () => {
      const appBaseHrefProvider = appConfig.providers.find(
        (p: any) => p.provide === APP_BASE_HREF,
      );
      expect(appBaseHrefProvider).toBeDefined();

      if (appBaseHrefProvider) {
        if ('useValue' in appBaseHrefProvider) {
          expect(appBaseHrefProvider.useValue).toBe('/ui/');
        }
      }
    });

    describe('App Routing', () => {
      let router: Router;
      let location: Location;

      beforeEach(() => {
        TestBed.configureTestingModule({
          imports: [BrowserAnimationsModule],
          providers: [
            {
              provide: AuthGuard,
              useClass: MockAuthGuard,
            },
            provideRouter(routes),
            provideHttpClient(),
            provideHttpClientTesting(),
          ],
        });

        router = TestBed.inject(Router);
        location = TestBed.inject(Location);

        router.navigateByUrl('/');
      });

      it('should navigate to /login for the login route', fakeAsync(() => {
        router.navigate(['/login']);
        tick();
        expect(location.path()).toBe('/login');
      }));

      it('should navigate to /token for the token route', fakeAsync(() => {
        router.navigate(['/token']);
        tick();
        expect(location.path()).toBe('/token');
      }));

      it('should redirect unknown routes (**) to /login', fakeAsync(() => {
        router.navigate(['/unknown-route']);
        tick();
        expect(location.path()).toBe('/login');
      }));
    });
  });
});
