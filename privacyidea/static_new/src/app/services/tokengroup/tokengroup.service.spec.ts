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
import { TokengroupService } from "./tokengroup.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { signal } from "@angular/core";
import { MockContentService, MockPiResponse } from "../../../testing/mock-services";
import { ContentService } from "../content/content.service";

describe("TokengroupService", () => {
  let service: TokengroupService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;

  beforeEach(() => {
    const authServiceMock = {
      getHeaders: jest.fn().mockReturnValue({})
    };
    const notificationServiceMock = {
      openSnackBar: jest.fn(),
      handleResourceError: jest.fn()
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
    service = TestBed.inject(TokengroupService);
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

  it("should post tokengroup", async () => {
    const group = { groupname: "test", description: "desc" };
    const promise = service.postTokengroup(group);

    const req = httpMock.expectOne(`${environment.proxyUrl}/tokengroup/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully saved tokengroup.");
  });

  it("should delete tokengroup", async () => {
    const promise = service.deleteTokengroup("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/tokengroup/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted tokengroup: test.");
  });

  describe("tokengroupResource / tokengroups", () => {

    it("tokengroups falls back to default when resource empty", () => {
      expect(service.tokengroups()).toEqual([]);
    });

    it("should update smsGateways from smsGatewaysResource on successful response", async () => {
      contentService.onExternalTokenGroups = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/tokengroup/");
      expect(req.request.method).toBe("GET");
      const tokenGroups = {test: { description: "", id: 1 }};
      req.flush(MockPiResponse.fromValue(tokenGroups));
      await Promise.resolve();

      expect(service.tokengroups()).toEqual([{groupname: "test", description: "", id: 1 }]);
    });

    it("should handle error state from smsGatewayResource", async () => {
      contentService.onExternalTokenGroups = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/tokengroup/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.tokengroups()).toEqual([]);
    });
  });
});
