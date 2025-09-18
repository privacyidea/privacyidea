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
import { signal } from "@angular/core";
import { Router } from "@angular/router";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { MockNotificationService } from "../../../testing/mock-services";

describe("SessionTimerService", () => {
  let service: SessionTimerService;
  let router: { navigate: jest.Mock };
  let auth: { logoutTimeSeconds: ReturnType<typeof signal<number | undefined>>; logout: jest.Mock };
  let notify: MockNotificationService;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2025-01-01T00:00:00.000Z"));

    router = { navigate: jest.fn() };
    auth = {
      logoutTimeSeconds: signal<number | undefined>(undefined),
      logout: jest.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        SessionTimerService,
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: auth },
        { provide: NotificationService, useClass: MockNotificationService },
      ]
    });

    notify = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    service = TestBed.inject(SessionTimerService);
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
    expect(service.remainingTime()).toBeUndefined();
  });

  it("startTimer warns when logout time is not defined and does not schedule timeout", () => {
    const warnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
    service.startTimer();
    jest.advanceTimersByTime(60_000);
    expect(warnSpy).toHaveBeenCalledWith("Session timeout is not defined. Cannot start session timer.");
    expect(auth.logout).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it("startTimer schedules timeout and triggers logout + navigation on expiry", () => {
    auth.logoutTimeSeconds.set(2);
    const clearIntervalSpy = jest.spyOn(global, "clearInterval");

    service.startRefreshingRemainingTime();
    service.startTimer();

    jest.advanceTimersByTime(2000);

    expect(auth.logout).toHaveBeenCalled();
    expect(notify.openSnackBar).toHaveBeenCalledWith("Session expired. Redirecting to login page.");
    expect(router.navigate).toHaveBeenCalledWith(["login"]);
    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  it("resetTimer cancels a scheduled timeout", () => {
    auth.logoutTimeSeconds.set(1);
    service.startTimer();
    service.resetTimer();

    jest.advanceTimersByTime(2000);

    expect(auth.logout).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it("startRefreshingRemainingTime updates remainingTime every second", () => {
    auth.logoutTimeSeconds.set(10);

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
    auth.logoutTimeSeconds.set(31);
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
    auth.logoutTimeSeconds.set(5);
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
});