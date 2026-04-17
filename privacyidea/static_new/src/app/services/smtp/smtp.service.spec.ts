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
import { SmtpService } from "./smtp.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { signal } from "@angular/core";
import { MockContentService, MockPiResponse } from "../../../testing/mock-services";
import { ContentService } from "../content/content.service";

describe("SmtpService", () => {
  let service: SmtpService;
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

  it("should post SMTP server", async () => {
    const server = { identifier: "test", server: "smtp.test.com" } as any;
    const promise = service.postSmtpServer(server);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully saved SMTP server.");
  });

  it("should delete SMTP server", async () => {
    const promise = service.deleteSmtpServer("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted SMTP server: test.");
  });

  it("should test SMTP server", async () => {
    const params = { sender: "test@test.com" };
    const promise = service.testSmtpServer(params);

    const req = httpMock.expectOne(`${environment.proxyUrl}/smtpserver/send_test_email`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: true } });

    const result = await promise;
    expect(result).toBe(true);
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Test email sent successfully.");
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
        "test": {
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
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.smtpServers()).toEqual([]);
    });
  });
});