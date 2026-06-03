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
import { SmtpServer, SmtpService } from "./smtp.service";

describe("SmtpService", () => {
  let service: SmtpService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;

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

  describe("smtpServers", () => {
    it("smsGateways falls back to default when resource empty", () => {
      expect(service.smtpServers()).toEqual([]);
    });

    it("should update smtpServers from smtpServerResource on successful response", async () => {
      contentService.onExternalSmtp = signal(true);
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
  });
});
