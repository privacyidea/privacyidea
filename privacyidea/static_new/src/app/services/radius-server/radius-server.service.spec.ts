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
import { RadiusServerService } from "./radius-server.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { MockContentService, MockPiResponse } from "../../../testing/mock-services";
import { ContentService } from "../content/content.service";
import { signal } from "@angular/core";

describe("RadiusServerService", () => {
  let service: RadiusServerService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let authServiceMock: MockAuthService;
  let contentServiceMock: MockContentService;

  beforeEach(() => {
    const notificationServiceMock = {
      openSnackBar: jest.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(RadiusServerService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentServiceMock = TestBed.inject(ContentService) as any;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post RADIUS server", async () => {
    const server = { identifier: "test", server: "1.2.3.4", secret: "secret" } as any;
    const promise = service.postRadiusServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully saved RADIUS server.");
  });

  it("should delete RADIUS server", async () => {
    const promise = service.deleteRadiusServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted RADIUS server: test.");
  });

  it("should test RADIUS server", async () => {
    const params = { server: "1.2.3.4", secret: "secret" };
    const promise = service.testRadiusServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/test_request`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: true } });

    const result = await promise;
    expect(result).toBe(true);
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("RADIUS request successful.");
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

      let req = httpMock.expectOne(`${environment.proxyUrl}/radiusserver/`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.radiusServers()).toEqual([]);
    });
  });
});
