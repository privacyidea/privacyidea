import {TestBed} from '@angular/core/testing';
import {Router} from '@angular/router';
import {AuthGuard} from './auth.guard';
import {AuthService} from '../services/auth/auth.service';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {
    // Create spies for AuthService and Router
    const authServiceMock = jasmine.createSpyObj('AuthService', ['isAuthenticatedUser']);
    const routerMock = jasmine.createSpyObj('Router', ['navigate']);

    // Make the router's navigate spy return a resolved promise
    routerMock.navigate.and.returnValue(Promise.resolve(true));

    TestBed.configureTestingModule({
      providers: [
        AuthGuard,
        {provide: AuthService, useValue: authServiceMock},
        {provide: Router, useValue: routerMock},
      ],
    });

    guard = TestBed.inject(AuthGuard);
    authServiceSpy = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });

  it('should allow activation if the user is authenticated', () => {
    // Arrange: Set up the mock to return true for isAuthenticatedUser
    authServiceSpy.isAuthenticatedUser.and.returnValue(true);

    // Act: Call canActivate and canActivateChild
    const canActivateResult = guard.canActivate();
    const canActivateChildResult = guard.canActivateChild();

    // Assert: Both should return true
    expect(canActivateResult).toBeTrue();
    expect(canActivateChildResult).toBeTrue();
    expect(authServiceSpy.isAuthenticatedUser).toHaveBeenCalledTimes(2);
  });

  it('should block activation and navigate if the user is not authenticated', (done) => {
    // Arrange: Set up the mock to return false for isAuthenticatedUser
    authServiceSpy.isAuthenticatedUser.and.returnValue(false);

    // Act: Call canActivate and canActivateChild
    const canActivateResult = guard.canActivate();
    const canActivateChildResult = guard.canActivateChild();

    // Assert: Both should return false and router.navigate should be called
    expect(canActivateResult).toBeFalse();
    expect(canActivateChildResult).toBeFalse();
    expect(authServiceSpy.isAuthenticatedUser).toHaveBeenCalledTimes(2);
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);

    // Ensure that the router navigation promise is handled properly
    routerSpy.navigate.calls.mostRecent().returnValue.then(() => {
      done();
    });
  });
});
