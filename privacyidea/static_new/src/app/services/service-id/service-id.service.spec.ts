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
import { ServiceIdService } from "./service-id.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { MockContentService, MockPiResponse } from "../../../testing/mock-services";
import { ContentService } from "../content/content.service";
import { ROUTE_PATHS } from "../../route_paths";
import { lastValueFrom, of } from "rxjs";

describe("ServiceIdService", () => {
  let service: ServiceIdService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;

  beforeEach(() => {
    const authServiceMock = {
      getHeaders: jest.fn().mockReturnValue({})
    };
    const notificationServiceMock = {
      openSnackBar: jest.fn()
    };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(ServiceIdService);
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

  it("should post service ID", async () => {
    const serviceId = { servicename: "test", description: "desc" };
    const promise = service.postServiceId(serviceId);

    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully saved service ID.");
  });

  it("should delete service ID", async () => {
    const promise = service.deleteServiceId("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/serviceid/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted service ID: test.");
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
        status: 403, statusText: "Permission denied"
      });
    await lastValueFrom(of({})); // Wait for async updates

    expect(service.serviceIdResource.hasValue()).toEqual(false)
    expect(service.serviceIds()).toEqual([]);
  });
});
