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
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { SmtpServer, SmtpService } from "./smtp.service";

describe("SmtpService", () => {
  let service: SmtpService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;
  let authService: MockAuthService;

  // The list is only requested by an admin holding smtpserver_read, which a default install does.
  const allowSmtpRead = () =>
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["smtpserver_read"] });

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        SmtpService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(SmtpService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  const buildSmtpServer = (): SmtpServer => ({
    identifier: "test",
    server: "smtp.test.com",
    port: 25,
    timeout: 120,
    sender: "",
    tls: true,
    enqueue_job: false,
    smime: false,
    dont_send_on_error: true
  });

  it("should post SMTP server", async () => {
    const server = buildSmtpServer();
    const promise = service.postSmtpServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/test`);
    expect(req.request.method).toBe("POST");
    req.flush(MockPiResponse.fromValue(true));

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully saved SMTP server.");
  });

  it("should show error notification when posting SMTP server fails", async () => {
    const server = buildSmtpServer();
    const promise = service.postSmtpServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/test`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to save SMTP server. Something went wrong");
  });

  it("should delete SMTP server", async () => {
    const promise = service.deleteSmtpServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully deleted SMTP server: test.");
  });

  it("should show error notification when deleting SMTP server fails", async () => {
    const promise = service.deleteSmtpServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/test`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to delete SMTP server. Something went wrong");
  });

  it("should test SMTP server", async () => {
    const params = { ...buildSmtpServer(), sender: "test@test.com", recipient: "to@test.com" };
    const promise = service.testSmtpServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/send_test_email`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: true } });

    const result = await promise;
    expect(result).toBe(true);
    expect(notificationService.success).toHaveBeenCalledWith("Test email sent successfully.");
  });

  it("should show error notification when SMTP test request fails", async () => {
    const params = { ...buildSmtpServer(), sender: "test@test.com", recipient: "to@test.com" };
    const promise = service.testSmtpServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/send_test_email`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    const result = await promise;
    expect(result).toBe(false);
    expect(notificationService.error).toHaveBeenCalledWith("Failed to send test email. Something went wrong");
  });

  it("should return false when the SMTP test responds without a positive result", async () => {
    const params = { ...buildSmtpServer(), sender: "test@test.com", recipient: "to@test.com" };
    const promise = service.testSmtpServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/send_test_email`);
    req.flush({ result: { value: false } });

    await expect(promise).resolves.toBe(false);
    expect(notificationService.success).not.toHaveBeenCalled();
  });

  it("should list SMTP servers", () => {
    service.listSmtpServers().subscribe();

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/`);
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromValue({}));
  });

  describe("smtpServers", () => {
    it("smsGateways falls back to default when resource empty", () => {
      expect(service.smtpServers()).toEqual([]);
    });

    it("should update smtpServers from smtpServerResource on successful response", async () => {
      contentService.onExternalSmtp = signal(true);
      allowSmtpRead();
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/smtpserver/");
      expect(req.request.method).toBe("GET");
      const smtpServers = {
        test: {
          identifier: "test",
          server: "",
          port: 25,
          timeout: 120,
          sender: "",
          tls: true,
          enqueue_job: false,
          smime: false,
          dont_send_on_error: true
        }
      };
      req.flush(MockPiResponse.fromValue(smtpServers));
      await Promise.resolve();

      expect(service.smtpServers()).toEqual([smtpServers.test]);
    });

    it("should handle error state from smtpServerResource", async () => {
      contentService.onExternalSmtp = signal(true);
      allowSmtpRead();
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/smtpserver/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.smtpServers()).toEqual([]);
    });

    it("should return an empty list when the resource resolves without a value", async () => {
      contentService.onExternalSmtp = signal(true);
      allowSmtpRead();
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/smtpserver/");
      req.flush({ result: { status: true } });
      await Promise.resolve();

      expect(service.smtpServers()).toEqual([]);
    });

    // The conditional-access edit page picks the SMTP server for its email actions from this list.
    it("should fetch the servers for the conditional access pages", () => {
      contentService.routeUrl.set(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
      allowSmtpRead();
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/smtpserver/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromValue({}));
    });

    // Without the right the endpoint can only answer 403, which would raise an error notification on
    // a page that merely wanted to offer the identifiers, so nothing is requested at all.
    it("should not request the servers without smtpserver_read", () => {
      contentService.routeUrl.set(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
      TestBed.tick();

      httpMock.expectNone((r) => r.url === "/smtpserver/");
      expect(service.smtpServers()).toEqual([]);
    });
  });
});
