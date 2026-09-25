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

import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { ChallengesService } from "./challenges.service";
import { AuthService } from "@services/auth/auth.service";
import { TokenService } from "@services/token/token.service";
import { MockAuthService, MockContentService, MockTokenService } from "@testing/mock-services";
import { ContentService } from "@services/content/content.service";

describe("ChallengesService", () => {
  let challengesService: ChallengesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ChallengesService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    challengesService = TestBed.inject(ChallengesService);
  });

  it("should be created", () => {
    expect(challengesService).toBeTruthy();
  });

  it("should not include empty filter values in filterParams except for the serial", () => {
    challengesService.activeFilter.set(
      new FilterValue({
        value: "serial: '' transaction_id: ***"
      })
    );
    let params = challengesService.requestParams();
    expect(params).toHaveProperty("serial", "");
    expect(params).not.toHaveProperty("transaction_id");

    challengesService.activeFilter.set(
      new FilterValue({
        value: "serial: '123' transaction_id: '    '"
      })
    );
    params = challengesService.requestParams();
    expect(params).toHaveProperty("serial", "*123*");
    expect(params).not.toHaveProperty("transaction_id");
  });

  describe("challengesResource", () => {
    let authService: MockAuthService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      httpMock = TestBed.inject(HttpTestingController);
      (TestBed.inject(ContentService) as unknown as MockContentService).routeUrl.set(ROUTE_PATHS.TOKENS_CHALLENGES);
    });

    it("requests the challenges with getchallenges", () => {
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["getchallenges"] });
      TestBed.tick();

      httpMock.expectOne((r) => r.url.endsWith("challenges/"));
    });

    it("does not request the challenges without getchallenges", () => {
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
      TestBed.tick();

      httpMock.expectNone((r) => r.url.includes("challenges"));
    });
  });
});
