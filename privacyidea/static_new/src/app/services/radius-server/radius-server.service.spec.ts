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
import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { RadiusServer, RadiusServerService } from "./radius-server.service";

describe("RadiusServerService", () => {
  let service: RadiusServerService;
  let httpMock: HttpTestingController;
  let notificationServiceMock: MockNotificationService;
  let contentServiceMock: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        RadiusServerService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(RadiusServerService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post RADIUS server", async () => {
    const server: Partial<RadiusServer> = { identifier: "test", server: "1.2.3.4", secret: "secret" };
    const promise = service.postRadiusServer(server as RadiusServer);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test`);
    expect(req.request.method).toBe("POST");
    req.flush(MockPiResponse.fromValue(true));

    await promise;
    expect(notificationServiceMock.success).toHaveBeenCalledWith("Successfully saved RADIUS server.");
  });

  it("should show error notification when posting RADIUS server fails", async () => {
    const server: Partial<RadiusServer> = { identifier: "test", server: "1.2.3.4", secret: "secret" };
    const promise = service.postRadiusServer(server as RadiusServer);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to save RADIUS server. Something went wrong");
  });

  it("should delete RADIUS server", async () => {
    const promise = service.deleteRadiusServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationServiceMock.success).toHaveBeenCalledWith("Successfully deleted RADIUS server: test.");
  });

  it("should show error notification when deleting RADIUS server fails", async () => {
    const promise = service.deleteRadiusServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to delete RADIUS server. Something went wrong");
  });

  it("should test RADIUS server", async () => {
    const params = { server: "1.2.3.4", secret: "secret" };
    const promise = service.testRadiusServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test_request`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: true } });

    const result = await promise;
    expect(result).toBe(true);
    expect(notificationServiceMock.success).toHaveBeenCalledWith("RADIUS request successful.");
  });

  it("should show error notification when RADIUS test returns false", async () => {
    const params = { server: "1.2.3.4", secret: "secret" };
    const promise = service.testRadiusServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test_request`);
    req.flush({ result: { value: false } });

    const result = await promise;
    expect(result).toBe(false);
    expect(notificationServiceMock.error).toHaveBeenCalledWith("RADIUS request failed!");
  });

  it("should show error notification when RADIUS test request fails", async () => {
    const params = { server: "1.2.3.4", secret: "secret" };
    const promise = service.testRadiusServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test_request`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await promise;
    expect(notificationServiceMock.error).toHaveBeenCalledWith(
      "Failed to send RADIUS test request. Something went wrong"
    );
  });

  describe("radiusServers", () => {
    it("should default to empty array if resource is empty", () => {
      expect(service.radiusServers()).toEqual([]);
    });

    it("should update radiusServers from resource", async () => {
      contentServiceMock.onExternalRadius = signal(true);
      TestBed.tick();

      const radiusServers = {
        server1: { server: "1.2.3.4", secret: "abc" },
        server2: { server: "5.6.7.8", secret: "def" }
      };
      const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/`);
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromValue(radiusServers));
      await Promise.resolve();

      expect(service.radiusServers()).toEqual([
        { identifier: "server1", server: "1.2.3.4", secret: "abc" },
        { identifier: "server2", server: "5.6.7.8", secret: "def" }
      ]);
    });

    it("should fallback to empty array on error", async () => {
      contentServiceMock.onExternalRadius = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.radiusServers()).toEqual([]);
    });

    it("should reset to empty array when resource errors after successful load", async () => {
      contentServiceMock.onExternalRadius = signal(true);
      TestBed.tick();

      const radiusServers = {
        server1: { server: "1.2.3.4", secret: "abc" }
      };
      let req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/`);
      req.flush(MockPiResponse.fromValue(radiusServers));
      await Promise.resolve();
      expect(service.radiusServers()).toEqual([{ identifier: "server1", server: "1.2.3.4", secret: "abc" }]);

      service.radiusServerResource.reload();
      TestBed.tick();
      req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/`);
      req.flush("Error", { status: 500, statusText: "Server Error" });
      await Promise.resolve();

      expect(service.radiusServers()).toEqual([]);
    });
  });
});
