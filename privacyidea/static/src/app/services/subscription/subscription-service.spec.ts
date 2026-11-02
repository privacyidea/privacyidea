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
import { TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { SubscriptionService } from "./subscription.service";
import { MockContentService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { ContentService } from "@services/content/content.service";

describe("SubscriptionService", () => {
  let service: SubscriptionService;
  let httpMock: HttpTestingController;
  let notifyMock: MockNotificationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        SubscriptionService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });

    service = TestBed.inject(SubscriptionService);
    httpMock = TestBed.inject(HttpTestingController);
    notifyMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
  });

  describe("subscriptionsResource", () => {
    let authService: MockAuthService;
    let contentService: MockContentService;

    beforeEach(() => {
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      contentService = TestBed.inject(ContentService) as unknown as MockContentService;
      contentService.routeUrl.set(ROUTE_PATHS.SUBSCRIPTION);
    });

    it("requests the subscriptions with managesubscription", () => {
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["managesubscription"] });
      TestBed.tick();

      httpMock.expectOne(environment.proxyUrl + "/subscriptions/");
    });

    it("does not request the subscriptions without managesubscription", () => {
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
      TestBed.tick();

      httpMock.expectNone(environment.proxyUrl + "/subscriptions/");
    });
  });

  it("reload() should not throw", () => {
    expect(() => service.reload()).not.toThrow();
  });

  it("deleteSubscription should propagate error and show notification", (done) => {
    service.deleteSubscription("app1").subscribe({
      next: () => done.fail("should error"),
      error: () => {
        expect(notifyMock.error).toHaveBeenCalled();
        done();
      }
    });

    const req = httpMock.expectOne(environment.proxyUrl + "/subscriptions/app1");
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { error: { message: "bad" } } }, { status: 400, statusText: "Bad Request" });
  });

  it("uploadSubscriptionFile should propagate error and show notification", (done) => {
    const file = new File(["abc"], "subs.txt");
    service.uploadSubscriptionFile(file).subscribe({
      next: () => done.fail("should error"),
      error: () => {
        expect(notifyMock.error).toHaveBeenCalled();
        done();
      }
    });

    const req = httpMock.expectOne(environment.proxyUrl + "/subscriptions/");
    expect(req.request.method).toBe("POST");
    req.flush({ result: { error: { message: "bad" } } }, { status: 500, statusText: "Server Error" });
  });

  describe("expired subscription warning", () => {
    let authService: MockAuthService;
    const statusUrl = environment.proxyUrl + "/subscriptions/status";
    const serverRow = (subscription: string) => ({
      result: { status: true, value: [{ application: "privacyidea", is_server: true, subscription }] }
    });

    beforeEach(() => {
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    });

    const setStatus = (status: number) =>
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, subscription_status: status });

    const upload = () => service.uploadSubscriptionFile(new File(["abc"], "subs.txt")).subscribe();

    it.each([
      ["valid", 3],
      ["expiring", 3],
      ["none", 0]
    ])("replaces the status 2 after an upload when the server subscription is %s", (state, expected) => {
      setStatus(2);
      upload();
      httpMock.expectOne(environment.proxyUrl + "/subscriptions/").flush({ result: { status: true, value: true } });

      httpMock.expectOne(statusUrl).flush(serverRow(state));

      expect(authService.updateSubscriptionStatus).toHaveBeenCalledWith(expected);
      expect(authService.subscriptionStatus()).toBe(expected);
    });

    it.each(["expired", "exceeded"])("keeps the status 2 when the server subscription is still %s", (state) => {
      setStatus(2);
      upload();
      httpMock.expectOne(environment.proxyUrl + "/subscriptions/").flush({ result: { status: true, value: true } });

      httpMock.expectOne(statusUrl).flush(serverRow(state));

      expect(authService.updateSubscriptionStatus).not.toHaveBeenCalled();
      expect(authService.subscriptionStatus()).toBe(2);
    });

    it("replaces the status 2 after a delete", () => {
      setStatus(2);
      service.deleteSubscription("privacyidea").subscribe();
      httpMock
        .expectOne(environment.proxyUrl + "/subscriptions/privacyidea")
        .flush({ result: { status: true, value: true } });

      httpMock.expectOne(statusUrl).flush(serverRow("none"));

      expect(authService.subscriptionStatus()).toBe(0);
    });

    it.each([0, 1, 3])("does not ask the server when the status is %i", (status) => {
      setStatus(status);
      upload();
      httpMock.expectOne(environment.proxyUrl + "/subscriptions/").flush({ result: { status: true, value: true } });

      httpMock.expectNone(statusUrl);
    });

    it("keeps the status 2 when the status request fails", () => {
      const consoleError = jest.spyOn(console, "error").mockImplementation(() => undefined);
      setStatus(2);
      upload();
      httpMock.expectOne(environment.proxyUrl + "/subscriptions/").flush({ result: { status: true, value: true } });

      httpMock.expectOne(statusUrl).flush({}, { status: 500, statusText: "Server Error" });

      expect(authService.subscriptionStatus()).toBe(2);
      consoleError.mockRestore();
    });
  });
});
