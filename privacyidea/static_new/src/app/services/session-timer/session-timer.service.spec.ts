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
import { TestBed } from "@angular/core/testing";
import { SessionTimerService } from "./session-timer.service";
import { Router } from "@angular/router";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { MockNotificationService } from "../../../testing/mock-services";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";

describe("SessionTimerService", () => {
  let service: SessionTimerService;
  let router: { navigate: jest.Mock };
  let authService: MockAuthService;
  let notify: MockNotificationService;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(Date.parse("2025-01-01T00:00:00.000Z"));

    router = { navigate: jest.fn() };

    TestBed.configureTestingModule({
      providers: [
        SessionTimerService,
        { provide: Router, useValue: router },
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });

    notify = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    service = TestBed.inject(SessionTimerService);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("remainingTime is undefined when no logout time is configured", () => {
    authService.logoutTimeS.set(null);
    authService.jwtLogoutTimeS.set(null);
    expect(service.remainingTime()).toBeUndefined();
  });

  it("remainingTime uses jwt time if logout time is not set", () => {
    authService.logoutTimeS.set(null);
    authService.jwtLogoutTimeS.set(30);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect(service.remainingTime()).toEqual(30_000);
  });

  it("remainingTime uses logout time if jwt time is not set", () => {
    authService.logoutTimeS.set(20);
    authService.jwtLogoutTimeS.set(null);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect(service.remainingTime()).toEqual(20_000);
  });

  it("remainingTime allows 0 values", () => {
    authService.logoutTimeS.set(0);
    authService.jwtLogoutTimeS.set(null);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect(service.remainingTime()).toEqual(0);

    authService.logoutTimeS.set(null);
    authService.jwtLogoutTimeS.set(0);
    expect(service.remainingTime()).toEqual(0);

    authService.logoutTimeS.set(0);
    authService.jwtLogoutTimeS.set(0);
    expect(service.remainingTime()).toEqual(0);
  });

  it("remainingTime uses shortest time if both are given", () => {
    authService.logoutTimeS.set(20);
    authService.jwtLogoutTimeS.set(30);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect(service.remainingTime()).toEqual(20_000);

    authService.logoutTimeS.set(40);
    authService.jwtLogoutTimeS.set(30);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect(service.remainingTime()).toEqual(30_000);
  });

  it("startTimer warns when logout time is not defined and does not schedule timeout", () => {
    const warnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
    authService.logoutTimeS.set(null);
    authService.jwtLogoutTimeS.set(null);
    service.startTimer();
    jest.advanceTimersByTime(60_000);
    expect(warnSpy).toHaveBeenCalledWith("Session timeout is not defined. Cannot start session timer.");
    expect(authService.logout).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it("startTimer schedules timeout and triggers logout on expiry", () => {
    authService.logoutTimeS.set(2);
    const clearIntervalSpy = jest.spyOn(global, "clearInterval");

    service.startRefreshingRemainingTime();
    service.startTimer();

    jest.advanceTimersByTime(2000);
    expect(notify.openSnackBar).toHaveBeenCalledWith(
      "Your session has expired. You will be logged out and redirected to the login page.");
    jest.advanceTimersByTime(1500);
    expect(authService.logout).toHaveBeenCalled();
    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  it("resetTimer cancels a scheduled timeout", () => {
    authService.logoutTimeS.set(1);
    service.startTimer();
    service.resetTimer();

    jest.advanceTimersByTime(2000);

    expect(authService.logout).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it("startRefreshingRemainingTime updates remainingTime every second", () => {
    authService.logoutTimeS.set(10);

    service.startTimer();
    const initial = service.remainingTime()!;
    expect(initial).toBeGreaterThanOrEqual(10_000 - 5);

    service.startRefreshingRemainingTime();
    jest.advanceTimersByTime(3000);

    const after3s = service.remainingTime()!;
    expect(after3s).toBeLessThanOrEqual(7000 + 25);
    expect(after3s).toBeGreaterThanOrEqual(6500);
  });


  it("shows a 30s warning when remainingTime enters the 30–31s window", async () => {
    authService.logoutTimeS.set(31);
    service.startTimer();

    const snackSpy = jest.spyOn((service as any).notificationService, "openSnackBar");

    const t = Date.now();
    (service as any).startTime.set(t);
    (service as any).currentTime.set(t + 500);

    await Promise.resolve();
    jest.runOnlyPendingTimers();

    expect(snackSpy).toHaveBeenCalledWith("Session will expire in 30 seconds.");
  });


  it("remainingTime counts down relative to startTime when timer restarted", () => {
    authService.logoutTimeS.set(5);
    service.startRefreshingRemainingTime();

    service.startTimer();
    const initial = service.remainingTime()!;
    expect(initial).toBeGreaterThanOrEqual(4900);

    jest.advanceTimersByTime(2000);
    service.startTimer();
    (service as any).currentTime.set(Date.now());

    const resetValue = service.remainingTime()!;
    expect(resetValue).toBeGreaterThanOrEqual(4900);
    expect(resetValue).toBeLessThanOrEqual(5000);
  });

  it("logoutTimeMs clamps negative values to zero", () => {
    authService.logoutTimeS.set(-10);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect((service as any).logoutTimeMs()).toBe(0);
  });

  it("logoutTimeMs allows 0 value", () => {
    authService.logoutTimeS.set(0);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect((service as any).logoutTimeMs()).toBe(0);
  });

  it("logoutTimeMs returns correct value for positive input", () => {
    authService.logoutTimeS.set(100);
    (service as any).startTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect((service as any).logoutTimeMs()).toBe(100_000);
  });

  it("logoutTimeMs returns null for null input", () => {
    authService.logoutTimeS.set(null);
    expect((service as any).logoutTimeMs()).toBeNull();
  });

  it("jwtLogoutTimeMs clamps negative values to zero", () => {
    authService.jwtLogoutTimeS.set(-10);
    (service as any).loginTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect((service as any).jwtLogoutTimeMs()).toBe(0);
  });

  it("jwtLogoutTimeMs allows 0", () => {
    authService.jwtLogoutTimeS.set(0);
    (service as any).loginTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect((service as any).jwtLogoutTimeMs()).toBe(0);
  });

  it("jwtLogoutTimeMs returns correct value for positive input", () => {
    authService.jwtLogoutTimeS.set(100);
    (service as any).loginTime.set(Date.now());
    (service as any).currentTime.set(Date.now());
    expect((service as any).jwtLogoutTimeMs()).toBe(100_000);
  });

  it("jwtLogoutTimeMs returns null for null input", () => {
    authService.jwtLogoutTimeS.set(null);
    expect((service as any).jwtLogoutTimeMs()).toBeNull();
  });

  it("initiallyStartTimer sets loginTime, strats time refreshing and starts timer", () => {
    const startTimerSpy = jest.spyOn(service, "startTimer");
    const startRefreshingSpy = jest.spyOn(service, "startRefreshingRemainingTime");

    (service as any).startTime.set(Date.now() - 5000);
    (service as any).loginTime.set(Date.now() - 5000);
    (service as any).currentTime.set(Date.now() - 5000);

    service.initialTimerStart();

    expect((service as any).loginTime()).toBeGreaterThanOrEqual(Date.now() - 500);
    expect((service as any).startTime()).toBeGreaterThanOrEqual(Date.now() - 500);
    expect(startRefreshingSpy).toHaveBeenCalled();
    expect(startTimerSpy).toHaveBeenCalled();
  });
});