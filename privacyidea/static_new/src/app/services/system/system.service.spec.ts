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
import { SystemService } from "./system.service";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { AuthService } from "../auth/auth.service";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { MockContentService, MockPiResponse } from "../../../testing/mock-services";
import { environment } from "../../../environments/environment";
import { lastValueFrom, of } from "rxjs";
import { ROUTE_PATHS } from "../../route_paths";
import { ContentService } from "../content/content.service";
import { signal } from "@angular/core";

describe("SystemService", () => {
  let service: SystemService;
  let httpMock: HttpTestingController;
  let contentService: MockContentService;
  let authService: MockAuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        SystemService
      ]
    });
    service = TestBed.inject(SystemService);
    httpMock = TestBed.inject(HttpTestingController);
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("caConnectorResource should make a request if on allowed route and return response", async () => {
    async function testLoadResource() {
      const caConnectorResponse = { service1: {}, service2: {} };
      const mockResponse = MockPiResponse.fromValue(caConnectorResponse);
      TestBed.tick();
      const req = httpMock.expectOne(`${environment.proxyUrl}/system/names/caconnector`);
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      const response = service.caConnectorResource.value();
      expect(response).toBeDefined();
      expect(response).toEqual(mockResponse);
      expect(response?.result?.value).toEqual(caConnectorResponse);
      expect(service.caConnectors()).toEqual(caConnectorResponse);
    }

    authService.actionAllowed.mockImplementation((action) => action === "enrollCERTIFICATE");

    contentService.routeUrl.set(ROUTE_PATHS.CONFIGURATION_SYSTEM);
    await testLoadResource();

    // set not allowed route to trigger resource reload
    contentService.routeUrl.set(ROUTE_PATHS.CONFIGURATION_MACHINES);
    expect(service.caConnectorResource.value()).toBeUndefined();

    contentService.routeUrl.set(ROUTE_PATHS.CONFIGURATION_SYSTEM);
    await testLoadResource();

    // set not allowed route to trigger resource reload
    contentService.routeUrl.set(ROUTE_PATHS.TOKENS);
    expect(service.caConnectorResource.value()).toBeUndefined();

    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    contentService.onTokenEnrollmentLikely.set(true);
    await testLoadResource();
  });

  it("caConnectors should handle http error from caConnectorResource", async () => {
    authService.actionAllowed.mockImplementation((action) => action === "enrollCERTIFICATE");
    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    contentService.onTokenEnrollmentLikely.set(true);

    TestBed.tick();
    const req = httpMock.expectOne(`${environment.proxyUrl}/system/names/caconnector`);
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
      status: 403, statusText: "Permission denied"
    });
    await lastValueFrom(of({})); // Wait for async updates

    expect(service.caConnectorResource.hasValue()).toEqual(false);
    expect(service.caConnectors()).toEqual([]);
  });

  describe("systemConfigResource", () => {

    it("systemConfig and systemConfigInit fall back to default when resource empty", () => {
      expect(service.systemConfig()).toEqual({});
      expect(service.systemConfigInit()).toEqual({});
    });

    it("should update signals based on systemConfigResource on successful response", async () => {
      contentService.onConfigurationSystem = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/system/");
      expect(req.request.method).toBe("GET");
      const systemConfig = [{ name: "test", providermodule: "TestProvider", options: {}, headers: {} }];
      const systemConfigInit = { key1: "value1", key2: "value2" };
      let response = MockPiResponse.fromValue(systemConfig, {}, systemConfigInit);
      req.flush(response);
      await Promise.resolve();

      expect(service.systemConfig()).toEqual(systemConfig);
      expect(service.systemConfigInit()).toEqual(systemConfigInit);
    });

    it("should handle error state from smsGatewayResource", async () => {
      contentService.onConfigurationSystem = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/system/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.systemConfigResource.hasValue()).toEqual(false);
      expect(service.systemConfig()).toEqual({});
      expect(service.systemConfigInit()).toEqual({});
    });
  });

  describe("nodesResource", () => {

    it("nodes falls back to default when resource is empty", () => {
      expect(service.nodes()).toEqual([]);
    });

    it("should update nodes signal based on nodesResource on successful response", async () => {
      contentService.onConfigurationSystem = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/system/nodes");
      expect(req.request.method).toBe("GET");
      const nodes = [{ name: "test", uuid: "1234" }];
      let response = MockPiResponse.fromValue(nodes);
      req.flush(response);
      await Promise.resolve();

      expect(service.nodes()).toEqual(nodes);
    });

    it("should handle error state from nodesResource", async () => {
      contentService.onConfigurationSystem = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/system/nodes");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.nodesResource.hasValue()).toEqual(false);
      expect(service.nodes()).toEqual([]);
    });
  });

  describe("radiusServers", () => {

    beforeEach(() => {
      authService.actionAllowed.mockImplementation((action) => action === "enrollRADIUS");
    });

    it("radiusServers falls back to default when resource is empty", () => {
      expect(service.radiusServers()).toEqual([]);
    });

    it("should update radiusServers signal based on radiusServersResource on successful response", async () => {
      contentService.onConfigurationSystem = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/system/names/radius");
      expect(req.request.method).toBe("GET");
      const radiusServers = ["server1", "server2"];
      let response = MockPiResponse.fromValue(radiusServers);
      req.flush(response);
      await Promise.resolve();

      expect(service.radiusServers()).toEqual(radiusServers);
    });

    it("should handle error state from radiusServersResource", async () => {
      contentService.onConfigurationSystem = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/system/names/radius");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.radiusServerResource.hasValue()).toEqual(false);
      expect(service.radiusServers()).toEqual([]);
    });
  });
});