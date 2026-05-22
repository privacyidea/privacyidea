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
import { MockContentService, MockLocalService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { ClientsService } from "./clients.service";

describe("ClientsService", () => {
  let clientService: ClientsService;
  let contentService: MockContentService;
  let mockAuthService: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        ClientsService,
        MockLocalService,
        MockNotificationService
      ]
    });
    clientService = TestBed.inject(ClientsService);
    contentService = TestBed.inject(ContentService) as any;
    mockAuthService = TestBed.inject(AuthService) as any;
    mockAuthService.actionAllowed.mockImplementation((action: string) => action === "clienttype");
  });

  it("should be created", () => {
    expect(clientService).toBeTruthy();
  });

  it("should return undefined if route is not CLIENTS", async () => {
    contentService.routeUrl.update(() => ROUTE_PATHS.TOKENS);
    const mockBackend = TestBed.inject(HttpTestingController);
    TestBed.tick();

    // Expect and flush the HTTP request
    mockBackend.expectNone(environment.proxyUrl + "/client/");
    await Promise.resolve();

    expect(clientService.clientsResource.value()).toBeUndefined();
  });

  it("should return correct resource if route is CLIENTS", async () => {
    contentService.routeUrl.update(() => ROUTE_PATHS.CLIENTS);
    const mockBackend = TestBed.inject(HttpTestingController);
    TestBed.tick();

    // Expect and flush the HTTP request
    const req = mockBackend.expectOne(environment.proxyUrl + "/client/");
    req.flush({ result: {} });
    await Promise.resolve();

    expect(clientService.clientsResource.value()).toBeDefined();
  });

  it("triggers a request on a non-CLIENTS route after requestClientsForAutocomplete is called", async () => {
    contentService.routeUrl.update(() => ROUTE_PATHS.TOKENS);
    const mockBackend = TestBed.inject(HttpTestingController);
    TestBed.tick();
    mockBackend.expectNone(environment.proxyUrl + "/client/");

    clientService.requestClientsForAutocomplete();
    TestBed.tick();

    const req = mockBackend.expectOne(environment.proxyUrl + "/client/");
    req.flush({ result: { value: {} } });
    await Promise.resolve();

    expect(clientService.clientsResource.value()).toBeDefined();
  });

  it("is idempotent: calling requestClientsForAutocomplete twice only triggers one request", async () => {
    contentService.routeUrl.update(() => ROUTE_PATHS.TOKENS);
    const mockBackend = TestBed.inject(HttpTestingController);
    TestBed.tick();

    clientService.requestClientsForAutocomplete();
    clientService.requestClientsForAutocomplete();
    TestBed.tick();

    const req = mockBackend.expectOne(environment.proxyUrl + "/client/");
    req.flush({ result: { value: {} } });
    await Promise.resolve();
    mockBackend.verify();
  });
});
