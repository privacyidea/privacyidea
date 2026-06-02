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
import { MockContentService, MockPiResponse } from "@testing/mock-services";
import { SmsGatewayPayload, SmsGatewayService } from "./sms-gateway.service";

describe("SmsGatewayService", () => {
  let service: SmsGatewayService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentServiceMock: MockContentService;

  beforeEach(() => {
    const authServiceMock = {
      getHeaders: jest.fn().mockReturnValue({})
    };
    const notificationServiceMock = {
      success: jest.fn(),
      error: jest.fn(),
      warning: jest.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        SmsGatewayService,
        { provide: AuthService, useValue: authServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(SmsGatewayService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post SMS gateway", async () => {
    const gateway: SmsGatewayPayload = { name: "test", module: "mod" };
    const promise = service.postSmsGateway(gateway);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smsgateway`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully saved SMS gateway.");
  });

  it("should show error notification when posting SMS gateway fails", async () => {
    const gateway: SmsGatewayPayload = { name: "test", module: "mod" };
    const promise = service.postSmsGateway(gateway);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smsgateway`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to save SMS gateway. Something went wrong");
  });

  it("should delete SMS gateway", async () => {
    const promise = service.deleteSmsGateway("test/1");

    const req = httpMock.expectOne(`${environment.proxyUrl}/smsgateway/${encodeURIComponent("test/1")}`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully deleted SMS gateway: test/1.");
  });

  it("should show error notification when deleting SMS gateway fails", async () => {
    const promise = service.deleteSmsGateway("test/1");

    const req = httpMock.expectOne(`${environment.proxyUrl}/smsgateway/${encodeURIComponent("test/1")}`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to delete SMS gateway. Something went wrong");
  });

  describe("smsGateways", () => {
    it("smsGateways falls back to default when resource empty", () => {
      expect(service.smsGateways()).toEqual([]);
    });

    it("should update smsGateways from smsGatewaysResource on successful response", async () => {
      contentServiceMock.onExternalSms = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/smsgateway/");
      expect(req.request.method).toBe("GET");
      const smsGateways = [{ name: "test", providermodule: "TestProvider", options: {}, headers: {} }];
      req.flush(MockPiResponse.fromValue(smsGateways));
      await Promise.resolve();

      expect(service.smsGateways()).toEqual(smsGateways);

      httpMock.expectOne((r) => r.url === "/smsgateway/providers");
    });

    it("should handle error state from smsGatewayResource", async () => {
      contentServiceMock.onExternalSms = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/smsgateway/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.smsGateways()).toEqual([]);

      httpMock.expectOne((r) => r.url === "/smsgateway/providers");
    });
  });
});
