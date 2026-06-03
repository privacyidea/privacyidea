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
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { lastValueFrom, of } from "rxjs";
import { PrivacyideaServer, PrivacyideaServerService } from "./privacyidea-server.service";

describe("PrivacyideaServerService", () => {
  let service: PrivacyideaServerService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        PrivacyideaServerService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(PrivacyideaServerService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post privacyIDEA server", async () => {
    const server: PrivacyideaServer = {
      identifier: "test",
      id: "test",
      name: "test",
      url: "http://test",
      tls: true
    };
    const promise = service.postPrivacyideaServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully saved privacyIDEA server.");
  });

  it("should show error notification when posting privacyIDEA server fails", async () => {
    const server: PrivacyideaServer = {
      identifier: "test",
      id: "test",
      name: "test",
      url: "http://test",
      tls: true
    };
    const promise = service.postPrivacyideaServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to save privacyIDEA server. Something went wrong");
  });

  it("should delete privacyIDEA server", async () => {
    const promise = service.deletePrivacyideaServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully deleted privacyIDEA server: test.");
  });

  it("should show error notification when deleting privacyIDEA server fails", async () => {
    const promise = service.deletePrivacyideaServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to delete privacyIDEA server. Something went wrong");
  });

  it("should test privacyIDEA server", async () => {
    const params: PrivacyideaServer = {
      identifier: "test",
      id: "test",
      name: "test",
      url: "http://test",
      tls: false
    };
    const promise = service.testPrivacyideaServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test_request`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: true } });

    const result = await promise;
    expect(result).toBe(true);
    expect(notificationService.success).toHaveBeenCalledWith("Test request successful.");
  });

  it("should show error notification when privacyIDEA test returns false", async () => {
    const params: PrivacyideaServer = {
      identifier: "test",
      id: "test",
      name: "test",
      url: "http://test",
      tls: false
    };
    const promise = service.testPrivacyideaServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test_request`);
    req.flush({ result: { value: false } });

    const result = await promise;
    expect(result).toBe(false);
    expect(notificationService.error).toHaveBeenCalledWith("Test request failed.");
  });

  it("should show error notification when privacyIDEA test request fails", async () => {
    const params: PrivacyideaServer = {
      identifier: "test",
      id: "test",
      name: "test",
      url: "http://test",
      tls: false
    };
    const promise = service.testPrivacyideaServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test_request`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    const result = await promise;
    expect(result).toBe(false);
    expect(notificationService.error).toHaveBeenCalledWith("Failed to send test request. Something went wrong");
  });

  it("privacyideaServerResource should not do request and return undefined on unexpected route", () => {
    contentService.routeUrl.set(ROUTE_PATHS.TOKENS);
    const resource = service.remoteServerResource.value();
    expect(resource).toBeUndefined();
    // No HTTP request should be made
    const requests = httpMock.match(() => true);
    expect(requests.length).toBe(0);
  });

  it("privacyideaServerResource should make a request if on allowed route and return response", async () => {
    async function testLoadResource() {
      const piServerResponse = { pi1: {}, pi2: {} };
      const mockResponse = MockPiResponse.fromValue(piServerResponse);
      TestBed.tick();
      const req = httpMock.expectOne(service.privacyideaServerBaseUrl);
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      const response = service.remoteServerResource.value();
      expect(response).toBeDefined();
      expect(response).toEqual(mockResponse);
      expect(response?.result?.value).toEqual(piServerResponse);
    }

    contentService.routeUrl.set(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
    await testLoadResource();

    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    contentService.onTokenEnrollmentLikely.set(true);
    await testLoadResource();
  });

  it("privacyideaServerResource should handle http error", async () => {
    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    contentService.onTokenEnrollmentLikely.set(true);
    TestBed.tick();

    const req = httpMock.expectOne(service.privacyideaServerBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
      status: 403,
      statusText: "Permission denied"
    });
    await lastValueFrom(of({})); // Wait for async updates

    expect(service.remoteServerOptions()).toEqual([]);
  });
});
