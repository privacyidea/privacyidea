/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideZonelessChangeDetection } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { PiResponse } from "@app/app.component";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockAuthService, MockNotificationService } from "@testing/mock-services";
import { UserSettings, UserSettingsService } from "./user-settings.service";

describe("UserSettingsService", () => {
  let service: UserSettingsService;
  let httpMock: HttpTestingController;
  let notificationService: MockNotificationService;

  const respondWith = (settings: UserSettings, request = httpMock.expectOne("/user/settings")): void => {
    request.flush({ result: { status: true, value: settings } } as PiResponse<UserSettings>);
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        UserSettingsService
      ]
    });
    service = TestBed.inject(UserSettingsService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should fetch the settings document", () => {
    let result: UserSettings | null = null;
    service.getSettings().subscribe((settings) => {
      result = settings;
    });

    const request = httpMock.expectOne("/user/settings");
    expect(request.request.method).toBe("GET");
    respondWith({ theme: "dark" }, request);

    expect(result).toEqual({ theme: "dark" });
  });

  it("should serve later reads from the cache", () => {
    service.getSettings().subscribe();
    respondWith({ theme: "dark" });

    let result: UserSettings | null = null;
    service.getSettings().subscribe((settings) => {
      result = settings;
    });

    expect(result).toEqual({ theme: "dark" });
    httpMock.expectNone("/user/settings");
  });

  it("should share a single request between concurrent readers", () => {
    service.getSettings().subscribe();
    service.getSettings().subscribe();

    respondWith({ theme: "dark" });
  });

  it("should return a single setting", () => {
    let result: string | null = null;
    service.getSetting<string>("theme").subscribe((value) => {
      result = value;
    });
    respondWith({ theme: "dark" });

    expect(result).toBe("dark");
  });

  it("should return null for an absent setting", () => {
    let result: string | null = "unset";
    service.getSetting<string>("theme").subscribe((value) => {
      result = value;
    });
    respondWith({});

    expect(result).toBeNull();
  });

  it("should post a single setting as a partial update", () => {
    service.setSetting("theme", "dark").subscribe();

    const request = httpMock.expectOne("/user/settings");
    expect(request.request.method).toBe("POST");
    expect(request.request.body).toEqual({ settings: { theme: "dark" } });
    request.flush({ result: { status: true, value: { theme: "dark" } } });

    expect(service.settings()).toEqual({ theme: "dark" });
  });

  it("should update the cache from the stored document", () => {
    service.getSettings().subscribe();
    respondWith({ theme: "dark" });

    service.setSetting("starting_page", "tokens").subscribe();
    httpMock.expectOne("/user/settings").flush({
      result: { status: true, value: { theme: "dark", starting_page: "tokens" } }
    });

    let result: UserSettings | null = null;
    service.getSettings().subscribe((settings) => {
      result = settings;
    });
    expect(result).toEqual({ theme: "dark", starting_page: "tokens" });
  });

  it("should delete a single setting", () => {
    service.deleteSetting("dashboard").subscribe();

    const request = httpMock.expectOne("/user/settings/dashboard");
    expect(request.request.method).toBe("DELETE");
    request.flush({ result: { status: true, value: {} } });

    expect(service.settings()).toEqual({});
  });

  it("should notify and rethrow when a request fails", () => {
    let failed = false;
    service.getSettings().subscribe({ error: () => (failed = true) });
    httpMock.expectOne("/user/settings").flush("nope", { status: 500, statusText: "Server Error" });

    expect(failed).toBe(true);
    expect(notificationService.error).toHaveBeenCalled();
  });

  it("should retry after a failed request instead of replaying the error", () => {
    service.getSettings().subscribe({ error: () => undefined });
    httpMock.expectOne("/user/settings").flush("nope", { status: 500, statusText: "Server Error" });

    let result: UserSettings | null = null;
    service.getSettings().subscribe((settings) => {
      result = settings;
    });
    respondWith({ theme: "light" });

    expect(result).toEqual({ theme: "light" });
  });

  it("should drop the cached document on clearCache", () => {
    service.getSettings().subscribe();
    respondWith({ theme: "dark" });

    service.clearCache();

    expect(service.settings()).toBeNull();
    service.getSettings().subscribe();
    respondWith({});
  });
});
