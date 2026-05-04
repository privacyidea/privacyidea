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
import { TestBed } from "@angular/core/testing";
import { PrivacyideaServerService } from "./privacyidea-server.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { ROUTE_PATHS } from "../../route_paths";
import { MockContentService, MockNotificationService, MockPiResponse } from "../../../testing/mock-services";
import { lastValueFrom, of } from "rxjs";
import { ContentService } from "../content/content.service";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";

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
    const server = { identifier: "test", url: "http://test", tls: true } as any;
    const promise = service.postPrivacyideaServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully saved privacyIDEA server.");
  });

  it("should delete privacyIDEA server", async () => {
    const promise = service.deletePrivacyideaServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted privacyIDEA server: test.");
  });

  it("should test privacyIDEA server", async () => {
    const params = { url: "http://test" };
    const promise = service.testPrivacyideaServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/privacyideaserver/test_request`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: true } });

    const result = await promise;
    expect(result).toBe(true);
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Test request successful.");
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
        status: 403, statusText: "Permission denied"
      });
    await lastValueFrom(of({})); // Wait for async updates

    expect(service.remoteServerOptions()).toEqual([]);
  });
});
