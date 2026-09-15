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
import { Integration } from "@services/integrations/integrations.service";
import { MockAuthService, MockContentService, MockPiResponse } from "@testing/mock-services";
import { lastValueFrom, of } from "rxjs";
import { IntegrationsService } from "./integrations.service";

const CP: Integration = {
  id: "privacyidea-cp",
  label: "Windows Credential Provider",
  agent_names: ["privacyidea-cp"],
  policy_value: "privacyidea-cp",
  product_id: "privacyidea-cp",
  api_client: true,
  dashboard: true,
  section: "System Login",
  ptl_slug: "privacyidea-windows-credential-provider",
  github_repo: "privacyidea/privacyidea-credential-provider"
};

const WEBUI: Integration = {
  id: "privacyidea-webui",
  label: "privacyIDEA WebUI",
  agent_names: ["privacyIDEA-WebUI"],
  policy_value: "privacyIDEA-WebUI",
  product_id: null,
  api_client: false,
  dashboard: false,
  section: null,
  ptl_slug: null,
  github_repo: null
};

describe("IntegrationsService", () => {
  let service: IntegrationsService;
  let httpMock: HttpTestingController;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        IntegrationsService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(IntegrationsService);
    httpMock = TestBed.inject(HttpTestingController);
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should not request on a route with no integrations consumer", () => {
    contentService.routeUrl.set(ROUTE_PATHS.EVENTS);
    const resource = service.integrationsResource.value();
    expect(resource).toBeUndefined();
    expect(httpMock.match(() => true).length).toBe(0);
  });

  it("should request and populate integrations on the dashboard, policies and api-clients routes", async () => {
    async function testLoadResource(routeUrl: string) {
      contentService.routeUrl.set(routeUrl);
      TestBed.tick();
      const req = httpMock.expectOne(`${environment.proxyUrl}/info/integrations`);
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromValue([CP, WEBUI]));
      await lastValueFrom(of({}));
      expect(service.integrations()).toEqual([CP, WEBUI]);
    }

    // onDashboard is a plain signal on the mock, not derived from routeUrl - set explicitly,
    // and back to false afterwards so the later routeUrl-driven checks are actually re-tracked
    // (leaving it true would make the resource's dependency-tracked read short-circuit there).
    contentService.onDashboard.set(true);
    await testLoadResource(ROUTE_PATHS.DASHBOARD);
    contentService.onDashboard.set(false);

    await testLoadResource(ROUTE_PATHS.POLICIES);
    await testLoadResource(ROUTE_PATHS.POLICIES_API_CLIENTS);
  });

  it("should filter to API-client integrations", () => {
    service.integrations.set([CP, WEBUI]);
    expect(service.apiClientIntegrations()).toEqual([CP]);
  });

  it("should filter to dashboard integrations", () => {
    service.integrations.set([CP, WEBUI]);
    expect(service.dashboardIntegrations()).toEqual([CP]);
  });

  it("should look up a label by id, falling back to the raw id", () => {
    service.integrations.set([CP]);
    expect(service.labelFor("privacyidea-cp")).toBe("Windows Credential Provider");
    expect(service.labelFor("unknown")).toBe("unknown");
  });

  it("should look up a label by policy_value case-insensitively, falling back to the raw value", () => {
    service.integrations.set([CP]);
    expect(service.labelForPolicyValue("Privacyidea-CP")).toBe("Windows Credential Provider");
    expect(service.labelForPolicyValue("unknown-agent")).toBe("unknown-agent");
  });
});
