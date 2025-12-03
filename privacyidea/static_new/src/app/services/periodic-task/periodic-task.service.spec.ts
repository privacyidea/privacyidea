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

import { EMPTY_PERIODIC_TASK, PERIODIC_TASK_MODULES, PeriodicTaskService } from "./periodic-task.service";
import { MockContentService, MockNotificationService } from "../../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { TestBed } from "@angular/core/testing";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { NotificationService } from "../notification/notification.service";

describe("PeriodicTaskService", () => {
  let service: PeriodicTaskService;
  let httpTestingController: HttpTestingController;
  let authMock: MockAuthService;
  let contentMock: MockContentService;
  let notificationMock: MockNotificationService;

  beforeEach(() => {
    authMock = new MockAuthService();
    contentMock = new MockContentService();
    notificationMock = new MockNotificationService();

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        PeriodicTaskService,
        { provide: AuthService, useValue: authMock },
        { provide: ContentService, useValue: contentMock },
        { provide: NotificationService, useValue: notificationMock }
      ]
    });

    service = TestBed.inject(PeriodicTaskService);
    httpTestingController = TestBed.inject(HttpTestingController);
    contentMock.routeUrl.set("/configuration/periodictasks");
  });

  afterEach(() => {
    httpTestingController.verify();
    jest.restoreAllMocks();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should enable a periodic task", async () => {
    const mockResponse = { result: { status: true, value: "4" } };
    const promise = service.enablePeriodicTask("4");
    const req = httpTestingController.expectOne(
      r => r.url.includes("periodictask/enable/4") && r.method === "POST"
    );
    expect(req.request.body).toEqual({});
    req.flush(mockResponse);
    const result = await promise;
    expect(result).toEqual(mockResponse);
  });

  it("should handle error when enabling a periodic task", async () => {
    service.periodicTasksResource.reload = jest.fn();
    const promise = service.enablePeriodicTask("4");
    const req = httpTestingController.expectOne(r => r.url.includes("periodictask/enable/4"));
    req.flush(null, { status: 401, statusText: "Enabling periodic task not allowed" });
    const result = await promise;
    expect(notificationMock.openSnackBar).toHaveBeenCalledWith("Failed to enable periodic task!");
    expect(service.periodicTasksResource.reload).toHaveBeenCalled();
    expect(result).toBeUndefined();
  });

  it("should disable a periodic task", async () => {
    const mockResponse = { result: { status: true, value: "4" } };
    const promise = service.disablePeriodicTask("6");
    const req = httpTestingController.expectOne(r => r.url.includes("periodictask/disable/6"));
    expect(req.request.body).toEqual({});
    req.flush(mockResponse);
    const result = await promise;
    expect(result).toEqual(mockResponse);
  });

  it("should handle error when disabling a periodic task", async () => {
    service.periodicTasksResource.reload = jest.fn();
    const promise = service.disablePeriodicTask("6");
    const req = httpTestingController.expectOne(r => r.url.includes("periodictask/disable/6"));
    req.flush(null, { status: 500, statusText: "Server Error" });
    const result = await promise;
    expect(notificationMock.openSnackBar).toHaveBeenCalledWith("Failed to disable periodic task!");
    expect(service.periodicTasksResource.reload).toHaveBeenCalled();
    expect(result).toBeUndefined();
  });

  it("should delete a periodic task", (done) => {
    const mockResponse = { status: true, value: "4" };
    service.deletePeriodicTask("4").subscribe((res) => {
      expect(res).toEqual(mockResponse);
      done();
    });
    const req = httpTestingController.expectOne(r => r.url.includes("periodictask/4") && r.method === "DELETE");
    req.flush(mockResponse);
  });

  it("should handle error when deleting a periodic task", (done) => {
    service.deletePeriodicTask("4").subscribe({
      error: (err) => {
        expect(notificationMock.openSnackBar).toHaveBeenCalledWith("Failed to delete periodic task. ");
        done();
      }
    });
    const req = httpTestingController.expectOne(r => r.url.includes("4") && r.method === "DELETE");
    req.flush({ result: { error: { message: "fail" } } }, { status: 400, statusText: "Bad Request" });
  });

  it("should save a periodic task", (done) => {
    const mockResponse = { result: EMPTY_PERIODIC_TASK };
    service.savePeriodicTask(EMPTY_PERIODIC_TASK).subscribe((res) => {
      expect(res?.result).toEqual(EMPTY_PERIODIC_TASK);
      done();
    });
    const req = httpTestingController.expectOne(r => r.url.includes("/periodictask/") && r.method === "POST");
    req.flush(mockResponse);
  });

  it("should handle error when saving a periodic task", (done) => {
    service.savePeriodicTask(EMPTY_PERIODIC_TASK).subscribe((response) => {
        expect(response).toBeUndefined();
        expect(notificationMock.openSnackBar).toHaveBeenCalledWith("Failed to save periodic task. failure message");
        done();
    });
    const req = httpTestingController.expectOne(r => r.url.includes("/periodictask/") && r.method === "POST");
    req.flush({ result: { error: { message: "failure message" } } }, { status: 400, statusText: "Bad Request" });
  });

  it("should fetch all module options", () => {
    const mockOptions = { result: { value: { opt1: { type: "str", description: "desc" } } } };
    service.moduleOptions.set = jest.fn();
    service.fetchAllModuleOptions();
    PERIODIC_TASK_MODULES.forEach(module => {
      const req = httpTestingController.expectOne(r => r.url.includes(`periodictask/options/${module}`));
      req.flush(mockOptions);
    });
    expect(service.moduleOptions.set).toHaveBeenCalledWith(
      expect.objectContaining({
        SimpleStats: expect.any(Object),
        EventCounter: expect.any(Object)
      })
    );
  });

  it("should handle error when fetching module options", () => {
    service.fetchAllModuleOptions();
    // Only flush error for the first request; others will be cancelled
    const reqs = PERIODIC_TASK_MODULES.map(module =>
      httpTestingController.expectOne(r => r.url.includes(`periodictask/options/${module}`))
    );
    reqs[0].flush(null, { status: 500, statusText: "Server Error" });
    // Do NOT flush the rest, as they are cancelled
    expect(notificationMock.openSnackBar).toHaveBeenCalledWith("Failed to fetch module options.");
  });
});
