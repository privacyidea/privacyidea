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
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockNotificationService } from "@testing/mock-services/mock-notification-service";
import { PolicyTemplate, PolicyTemplateIndex, PolicyTemplatesService } from "./policy-templates.service";

describe("PolicyTemplatesService", () => {
  let service: PolicyTemplatesService;
  let httpMock: HttpTestingController;
  let authMock: MockAuthService;
  let notificationMock: MockNotificationService;

  const baseUrl = "policy-templates/";

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        PolicyTemplatesService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    service = TestBed.inject(PolicyTemplatesService);
    httpMock = TestBed.inject(HttpTestingController);
    TestBed.tick();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
    httpMock.expectOne(`${baseUrl}index.json`).flush({});
  });

  it("fetches the index from the URL provided by the auth service", () => {
    const remoteIndex: PolicyTemplateIndex = { tpl_a: "First", tpl_b: "Second" };
    const req = httpMock.expectOne(`${baseUrl}index.json`);
    expect(req.request.method).toBe("GET");
    req.flush(remoteIndex);

    expect(service.policyTemplatesIndex()).toEqual(remoteIndex);
  });

  it("resets to an empty index when the fetch fails", () => {
    const req = httpMock.expectOne(`${baseUrl}index.json`);
    req.error(new ProgressEvent("network error"));

    expect(service.policyTemplatesIndex()).toEqual({});
  });

  it("fetches an individual template from the configured URL", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    const remoteTemplate: PolicyTemplate = {
      name: "webui1",
      scope: "webui",
      action: { login_mode: "privacyIDEA" }
    };
    let received: PolicyTemplate | undefined;
    service.getTemplate("webui1").subscribe((tpl) => (received = tpl));

    const req = httpMock.expectOne(`${baseUrl}webui1.json`);
    expect(req.request.method).toBe("GET");
    req.flush(remoteTemplate);

    expect(received).toEqual(remoteTemplate);
  });

  it("caches subsequent template fetches", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    service.getTemplate("webui1").subscribe();
    httpMock.expectOne(`${baseUrl}webui1.json`).flush({ name: "webui1", scope: "webui" });

    let cached: PolicyTemplate | undefined;
    service.getTemplate("webui1").subscribe((tpl) => (cached = tpl));
    httpMock.expectNone(`${baseUrl}webui1.json`);

    expect(cached).toEqual({ name: "webui1", scope: "webui" });
  });

  it("yields undefined when a template fetch fails", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    let received: PolicyTemplate | undefined = { name: "sentinel", scope: "x" };
    service.getTemplate("webui1").subscribe((tpl) => (received = tpl));
    httpMock.expectOne(`${baseUrl}webui1.json`).error(new ProgressEvent("network error"));

    expect(received).toBeUndefined();
  });

  it("uses an absolute URL verbatim without prefixing the dev proxy", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "https://example.com/templates/" }));
    TestBed.tick();

    httpMock.expectOne("https://example.com/templates/index.json").flush({ x: "remote" });
    expect(service.policyTemplatesIndex()).toEqual({ x: "remote" });
  });

  it("ignores the legacy /static/policy-templates/ default and keeps using the bundled URL", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({ tpl: "bundled" });

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "/static/policy-templates/" }));
    TestBed.tick();

    // The legacy default must NOT trigger a request to /proxy/static/policy-templates/ —
    // it resolves to the same bundled URL we already fetched.
    httpMock.expectNone("/proxy/static/policy-templates/index.json");
    httpMock.expectNone("/static/policy-templates/index.json");

    let received: PolicyTemplate | undefined;
    service.getTemplate("webui1").subscribe((tpl) => (received = tpl));
    const req = httpMock.expectOne(`${baseUrl}webui1.json`);
    req.flush({ name: "webui1", scope: "webui" });
    expect(received).toEqual({ name: "webui1", scope: "webui" });
  });

  it("notifies on index fetch failure", () => {
    const errorSpy = jest.spyOn(notificationMock, "error");
    httpMock.expectOne(`${baseUrl}index.json`).error(new ProgressEvent("network error"));
    expect(errorSpy).toHaveBeenCalled();
  });

  it("falls back to the requested template name when the response omits it", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    let received: PolicyTemplate | undefined;
    service.getTemplate("webui1").subscribe((tpl) => (received = tpl));
    httpMock.expectOne(`${baseUrl}webui1.json`).flush({ scope: "webui" });

    expect(received).toEqual({ name: "webui1", scope: "webui" });
  });

  it("appends a trailing slash to a configured URL that is missing one", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "https://example.com/templates" }));
    TestBed.tick();

    httpMock.expectOne("https://example.com/templates/index.json").flush({});
  });

  it("prefixes absolute-path URLs with the dev proxy", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "/custom/templates/" }));
    TestBed.tick();

    // In tests `environment.proxyUrl` is empty, so the prefix is a no-op but the
    // branch that builds `${environment.proxyUrl}${url}` is exercised.
    httpMock.expectOne("/custom/templates/index.json").flush({});
  });

  it("does not refetch when the auth signal changes but resolves to the same URL", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    // Trigger the effect with a value that still resolves to the same bundled URL.
    authMock.authData.update((data) => ({ ...data! }));
    TestBed.tick();

    httpMock.expectNone(`${baseUrl}index.json`);
  });

  it("ignores a stale index response when the base URL has changed mid-flight", () => {
    const firstReq = httpMock.expectOne(`${baseUrl}index.json`);

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "https://example.com/templates/" }));
    TestBed.tick();
    const secondReq = httpMock.expectOne("https://example.com/templates/index.json");

    // The stale response must not overwrite the index for the current URL.
    firstReq.flush({ stale: "value" });
    expect(service.policyTemplatesIndex()).toEqual({});

    secondReq.flush({ fresh: "value" });
    expect(service.policyTemplatesIndex()).toEqual({ fresh: "value" });
  });

  it("suppresses error notifications for a stale index fetch", () => {
    const errorSpy = jest.spyOn(notificationMock, "error");
    const firstReq = httpMock.expectOne(`${baseUrl}index.json`);

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "https://example.com/templates/" }));
    TestBed.tick();
    const secondReq = httpMock.expectOne("https://example.com/templates/index.json");

    firstReq.error(new ProgressEvent("network error"));
    expect(errorSpy).not.toHaveBeenCalled();

    secondReq.flush({});
  });

  it("re-fetches a template after a previous fetch failed", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    let firstReceived: PolicyTemplate | undefined = { name: "sentinel", scope: "x" };
    service.getTemplate("webui1").subscribe((tpl) => (firstReceived = tpl));
    httpMock.expectOne(`${baseUrl}webui1.json`).error(new ProgressEvent("network error"));
    expect(firstReceived).toBeUndefined();

    // The cached failure must have been evicted so a retry actually hits the network.
    let secondReceived: PolicyTemplate | undefined;
    service.getTemplate("webui1").subscribe((tpl) => (secondReceived = tpl));
    const retry = httpMock.expectOne(`${baseUrl}webui1.json`);
    retry.flush({ name: "webui1", scope: "webui" });
    expect(secondReceived).toEqual({ name: "webui1", scope: "webui" });
  });
});
