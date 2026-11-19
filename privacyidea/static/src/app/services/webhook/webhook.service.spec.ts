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
import { TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { Webhook, WebhookService } from "./webhook.service";

describe("WebhookService", () => {
  let service: WebhookService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;
  let authService: MockAuthService;

  // /webhook/ requires webhook_read, so the resource only fires for an admin holding it.
  const allowWebhookRead = () =>
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["webhook_read"] });

  const buildWebhook = (): Webhook => ({
    identifier: "siem",
    url: "https://siem.example.com/hook",
    http_method: "POST",
    content_type: "application/json",
    auth_type: "none",
    verify_tls: true,
    timeout: 3,
    headers: {},
    secret_headers: []
  });

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        WebhookService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(WebhookService);
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

  it("does not request the list without webhook_read", () => {
    contentService.routeUrl.set(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
    TestBed.tick();
    // The guard skips the request rather than letting /webhook/ answer 403.
    httpMock.expectNone(`${environment.proxyUrl}/webhook/`);
  });

  it("lists the webhooks on the webhook page and exposes their identifiers", async () => {
    allowWebhookRead();
    contentService.routeUrl.set(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
    TestBed.tick();

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/`);
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromValue<Webhook[]>([buildWebhook()]));
    await Promise.resolve();

    expect(service.webhookIdentifiers()).toEqual(["siem"]);
  });

  it("posts a webhook and flattens the headers into header.* parameters", async () => {
    const webhook: Webhook = {
      ...buildWebhook(),
      headers: { "X-Api-Key": "s3cr3t", "X-Source": "privacyidea" },
      secret_headers: ["X-Api-Key"]
    };
    const promise = service.postWebhook(webhook);

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body["header.X-Api-Key"]).toBe("s3cr3t");
    expect(req.request.body["header.X-Source"]).toBe("privacyidea");
    // Only the header marked secret carries the flag, so a round-trip keeps the encryption state.
    expect(req.request.body["secret.header.X-Api-Key"]).toBe("1");
    expect(req.request.body["secret.header.X-Source"]).toBeUndefined();
    // The nested objects themselves are not sent; the server reads the flattened parameters.
    expect(req.request.body.headers).toBeUndefined();
    expect(req.request.body.secret_headers).toBeUndefined();
    req.flush(MockPiResponse.fromValue(1));

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully saved webhook.");
  });

  it("sends clear_headers when the header table was emptied", async () => {
    const promise = service.postWebhook(buildWebhook());

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem`);
    // No header.* parameter means "keep the stored set", so removing the last header needs this flag.
    expect(req.request.body["clear_headers"]).toBe(true);
    req.flush(MockPiResponse.fromValue(1));

    await promise;
  });

  it("reports a failed save", async () => {
    const promise = service.postWebhook(buildWebhook());

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to save webhook. Something went wrong");
  });

  it("deletes a webhook", async () => {
    const promise = service.deleteWebhook("siem");

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem`);
    expect(req.request.method).toBe("DELETE");
    req.flush(MockPiResponse.fromValue(1));

    await promise;
    expect(notificationService.success).toHaveBeenCalledWith("Successfully deleted webhook: siem.");
  });

  it("reports a failed delete", async () => {
    const promise = service.deleteWebhook("siem");

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notificationService.error).toHaveBeenCalledWith("Failed to delete webhook. Something went wrong");
  });

  it("reports what the endpoint answered on a successful test", async () => {
    const promise = service.testWebhook("siem");

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem/test`);
    expect(req.request.method).toBe("POST");
    req.flush(MockPiResponse.fromValue({ success: true, status_code: 200, response: "ok", error: null }));

    const result = await promise;
    expect(result?.success).toBe(true);
    expect(notificationService.success).toHaveBeenCalled();
  });

  it("treats a webhook that failed to deliver as a result, not an error", async () => {
    // A failed delivery is still HTTP 200 carrying success: false, which must be reported rather than thrown.
    const promise = service.testWebhook("siem");

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem/test`);
    req.flush(
      MockPiResponse.fromValue({ success: false, status_code: null, response: "", error: "connection refused" })
    );

    const result = await promise;
    expect(result?.success).toBe(false);
    expect(result?.error).toBe("connection refused");
    expect(notificationService.error).toHaveBeenCalled();
  });

  it("sends an overriding payload only when one is given", async () => {
    const promise = service.testWebhook("siem", "{\"ping\": true}");

    const req = httpMock.expectOne(`${environment.proxyUrl}/webhook/siem/test`);
    expect(req.request.body).toEqual({ payload: "{\"ping\": true}" });
    req.flush(MockPiResponse.fromValue({ success: true, status_code: 200, response: "", error: null }));

    await promise;
  });
});
