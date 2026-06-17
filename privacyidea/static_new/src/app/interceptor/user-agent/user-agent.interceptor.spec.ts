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

import { HttpHandlerFn, HttpHeaders, HttpRequest } from "@angular/common/http";
import { TestBed } from "@angular/core/testing";
import { VersioningService } from "@services/version/version.service";
import { MockVersioningService } from "@testing/mock-services";
import { EMPTY } from "rxjs";
import { userAgentInterceptor } from "./user-agent.interceptor";

describe("userAgentInterceptor", () => {
  const run = (req: HttpRequest<unknown>, next: HttpHandlerFn) =>
    TestBed.runInInjectionContext(() => userAgentInterceptor(req, next));
  let versioningService: MockVersioningService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [{ provide: VersioningService, useClass: MockVersioningService }]
    });

    versioningService = TestBed.inject(VersioningService) as MockVersioningService;
    versioningService.rawVersion.set("1.2.3.dev224");
    versioningService.version.set("1.2.3");
    versioningService.getVersion = jest.fn().mockReturnValue("1.2.3");
  });

  it("should add the User-Agent header with the correct version", (done) => {
    const req = new HttpRequest("GET", "/test");
    const next: HttpHandlerFn = (request) => {
      expect(request.headers.get("User-Agent")).toBe("privacyIDEA-WebUI/1.2.3.dev224");
      done();
      return EMPTY;
    };
    run(req, next);
  });

  it("should preserve other headers", (done) => {
    const req = new HttpRequest("GET", "/test", {
      headers: new HttpHeaders({ "PI-Authorization": "abc" })
    });
    const next: HttpHandlerFn = (request) => {
      expect(request.headers.get("PI-Authorization")).toBe("abc");
      expect(request.headers.get("User-Agent")).toBe("privacyIDEA-WebUI/1.2.3.dev224");
      done();
      return EMPTY;
    };
    run(req, next);
  });
});
