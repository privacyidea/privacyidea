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
import { POLICY_TEMPLATE_INDEX, POLICY_TEMPLATES } from "./policy-templates.constants";
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

  it("falls back to the bundled index when the fetch fails", () => {
    const req = httpMock.expectOne(`${baseUrl}index.json`);
    req.error(new ProgressEvent("network error"));

    expect(service.policyTemplatesIndex()).toEqual(POLICY_TEMPLATE_INDEX);
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

  it("falls back to the bundled template when the fetch fails", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    let received: PolicyTemplate | undefined;
    service.getTemplate("webui1").subscribe((tpl) => (received = tpl));
    httpMock.expectOne(`${baseUrl}webui1.json`).error(new ProgressEvent("network error"));

    expect(received).toEqual(POLICY_TEMPLATES["webui1"]);
  });

  it("uses an absolute URL verbatim without prefixing the dev proxy", () => {
    httpMock.expectOne(`${baseUrl}index.json`).flush({});

    authMock.authData.update((data) => ({ ...data!, policy_template_url: "https://example.com/templates/" }));
    TestBed.tick();

    httpMock.expectOne("https://example.com/templates/index.json").flush({ x: "remote" });
    expect(service.policyTemplatesIndex()).toEqual({ x: "remote" });
  });

  it("notifies on index fetch failure", () => {
    const errorSpy = jest.spyOn(notificationMock, "error");
    httpMock.expectOne(`${baseUrl}index.json`).error(new ProgressEvent("network error"));
    expect(errorSpy).toHaveBeenCalled();
  });
});
