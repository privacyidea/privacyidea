/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { ClientsService } from "./clients.service";
import {
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "../../../testing/mock-services";
import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ROUTE_PATHS } from "../../route_paths";
import { environment } from "../../../environments/environment";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";


describe("ClientsService", () => {
  let clientService: ClientsService;
  let contentService: MockContentService;

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
  });

  it("should be created", () => {
    expect(clientService).toBeTruthy();
  });

  it("should return undefined if route is not CLIENTS", async () => {
    contentService.routeUrl.update(() => ROUTE_PATHS.TOKENS);
    const mockBackend = TestBed.inject(HttpTestingController);
    TestBed.flushEffects();

    // Expect and flush the HTTP request
    mockBackend.expectNone(environment.proxyUrl + "/client/");
    await Promise.resolve();

    expect(clientService.clientsResource.value()).toBeUndefined();
  });

  it("should return correct resource if route is CLIENTS", async () => {
    contentService.routeUrl.update(() => ROUTE_PATHS.CLIENTS);
    const mockBackend = TestBed.inject(HttpTestingController);
    TestBed.flushEffects();

    // Expect and flush the HTTP request
    const req = mockBackend.expectOne(environment.proxyUrl + "/client/");
    req.flush({ result: {} });
    await Promise.resolve();

    expect(clientService.clientsResource.value()).toBeDefined();
  });
});
