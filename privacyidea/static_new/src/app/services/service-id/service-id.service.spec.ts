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
import { MockAuthService, MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { lastValueFrom, of } from "rxjs";
import { ServiceIdService } from "./service-id.service";

describe("ServiceIdService", () => {
  let service: ServiceIdService;
  let httpMock: HttpTestingController;
  let notifyMock: MockNotificationService;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ServiceIdService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(ServiceIdService);
    httpMock = TestBed.inject(HttpTestingController);
    notifyMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post service ID", async () => {
    const serviceId = { servicename: "test/1", description: "desc" };
    const promise = service.postServiceId(serviceId);

    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/${encodeURIComponent("test/1")}`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notifyMock.success).toHaveBeenCalledWith("Successfully saved service ID.");
  });

  it("should show error notification when posting service ID fails", async () => {
    const serviceId = { servicename: "test/1", description: "desc" };
    const promise = service.postServiceId(serviceId);

    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/${encodeURIComponent("test/1")}`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to save service ID. Something went wrong");
  });

  it("should delete service ID", async () => {
    const promise = service.deleteServiceId("test/1");

    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/${encodeURIComponent("test/1")}`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notifyMock.success).toHaveBeenCalledWith("Successfully deleted service ID: test/1.");
  });

  it("should show error notification when deleting service ID fails", async () => {
    const promise = service.deleteServiceId("test/1");

    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/${encodeURIComponent("test/1")}`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to delete service ID. Something went wrong");
  });

  it("serviceIdResource should not do request and return undefined on unexpected route", () => {
    contentService.routeUrl.set(ROUTE_PATHS.EVENTS);
    const resource = service.serviceIdResource.value();
    expect(resource).toBeUndefined();
    // No HTTP request should be made
    const requests = httpMock.match(() => true);
    expect(requests.length).toBe(0);
  });

  it("serviceIdResource should make a request if on allowed route and return response", async () => {
    async function testLoadResource() {
      const serviceIdResponse = { service1: {}, service2: {} };
      const mockResponse = MockPiResponse.fromValue(serviceIdResponse);
      TestBed.tick();
      const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/`);
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      const response = service.serviceIdResource.value();
      expect(response).toBeDefined();
      expect(response).toEqual(mockResponse);
      expect(response?.result?.value).toEqual(serviceIdResponse);
    }

    contentService.routeUrl.set(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    await testLoadResource();

    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    contentService.onTokenEnrollmentLikely.set(true);
    await testLoadResource();
  });

  it("Should handle http error of serviceIdResource", async () => {
    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    contentService.onTokenEnrollmentLikely.set(true);

    TestBed.tick();
    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/`);
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
      status: 403,
      statusText: "Permission denied"
    });
    await lastValueFrom(of({})); // Wait for async updates

    expect(service.serviceIdResource.hasValue()).toEqual(false);
    expect(service.serviceIds()).toEqual([]);
  });

  it("should reset to empty array when serviceIdResource errors after successful load", async () => {
    contentService.routeUrl.set(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    TestBed.tick();
    let req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/`);
    req.flush(MockPiResponse.fromValue({ svc1: { description: "d", id: 1 } }));
    await lastValueFrom(of({}));
    expect(service.serviceIds()).toEqual([{ servicename: "svc1", description: "d", id: 1 }]);

    service.serviceIdResource.reload();
    TestBed.tick();
    req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/`);
    req.flush("Error", { status: 500, statusText: "Server Error" });
    await lastValueFrom(of({}));

    expect(service.serviceIds()).toEqual([]);
  });
});
