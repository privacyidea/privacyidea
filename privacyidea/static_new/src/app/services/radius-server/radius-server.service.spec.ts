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

describe("RadiusServerService", () => {
  let service: RadiusServerService;
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
    service = TestBed.inject(RadiusServerService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post RADIUS server", async () => {
    const server = { identifier: "test", ip: "1.2.3.4", secret: "secret" } as any;
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
});
