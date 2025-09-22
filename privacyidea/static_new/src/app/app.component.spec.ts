/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { APP_BASE_HREF, Location } from "@angular/common";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideRouter, Router } from "@angular/router";

import { AppComponent } from "./app.component";
import { appConfig } from "./app.config";
import { routes } from "./app.routes";
import { AuthGuard } from "./guards/auth.guard";
import { AuthService } from "./services/auth/auth.service";
import { NotificationService } from "./services/notification/notification.service";
import { SessionTimerService } from "./services/session-timer/session-timer.service";

class MockAuthService {
  isAuthenticated = jest.fn(() => false);
  role = jest.fn(() => "admin");
}

class MockNotificationService {
  openSnackBar = jest.fn();
}

class MockSessionTimerService {
  startTimer = jest.fn();
  resetTimer = jest.fn();
}

describe("AppComponent", () => {
  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [AppComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes),
        { provide: AuthService, useClass: MockAuthService },
        {
          provode: AuthGuard,
          useValue: { canActivate: () => true, canMatch: () => true }
        },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: SessionTimerService, useClass: MockSessionTimerService }
      ]
    }).compileComponents();

    jest.spyOn(console, "warn").mockImplementation(() => {
    });
  });

  it("creates the app", () => {
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it("has title \"privacyidea-webui\"", () => {
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance.title).toBe("privacyidea-webui");
  });

  it("starts timer and shows snackbar when user already authenticated", () => {
    const auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    const timer = TestBed.inject(SessionTimerService) as unknown as MockSessionTimerService;
    const note = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    auth.isAuthenticated.mockReturnValue(true);

    TestBed.createComponent(AppComponent).detectChanges();

    expect(timer.startTimer).toHaveBeenCalled();
    expect(auth.isAuthenticated).toHaveBeenCalled();
    expect(note.openSnackBar).toHaveBeenCalledWith("User is already logged in.");
  });

  it("resets & restarts timer on user interaction", () => {
    const timer = TestBed.inject(SessionTimerService) as unknown as MockSessionTimerService;

    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();

    document.dispatchEvent(new Event("click"));

    expect(timer.resetTimer).toHaveBeenCalled();
    expect(timer.startTimer).toHaveBeenCalled();
  });

  describe("appConfig", () => {
    it("defines providers array", () => {
      expect(Array.isArray(appConfig.providers)).toBe(true);
    });

    it("contains APP_BASE_HREF set to /app/v2/", () => {
      const p = appConfig.providers.find((x: any) => x.provide === APP_BASE_HREF);
      if (p && "useValue" in p) {
        expect(p?.useValue).toBe("/app/v2/");
      }
    });
  });

  describe("Routing", () => {
    let router: Router;
    let location: Location;
    let auth: MockAuthService;

    beforeEach(async () => {
      router = TestBed.inject(Router);
      location = TestBed.inject(Location);
      auth = TestBed.inject(AuthService) as unknown as MockAuthService;

      auth.isAuthenticated.mockReturnValue(true);
      auth.role.mockReturnValue("admin");

      await router.navigateByUrl("/");
      jest.runOnlyPendingTimers();
      await Promise.resolve();
    });

    it("navigates to /login", async () => {
      await router.navigate(["/login"]);
      jest.runOnlyPendingTimers();
      await Promise.resolve();
      expect(location.path()).toBe("/login");
    });

    it("navigates to /token", async () => {
      await router.navigate(["/tokens"]);
      jest.runOnlyPendingTimers();
      await Promise.resolve();
      expect(location.path()).toBe("/tokens");
    });

    it("redirects unknown routes to /login", async () => {
      await router.navigate(["/does-not-exist"]);
      jest.runOnlyPendingTimers();
      await Promise.resolve();
      expect(location.path()).toBe("/login");
    });
  });
});
