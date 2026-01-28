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
import { PrivacyideaServerService } from "./privacyidea-server.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";

describe("PrivacyideaServerService", () => {
  let service: PrivacyideaServerService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;

  beforeEach(() => {
    const authServiceMock = {
      getHeaders: jest.fn().mockReturnValue({}),
    };
    const notificationServiceMock = {
      openSnackBar: jest.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
      ]
    });
    service = TestBed.inject(PrivacyideaServerService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
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
});
