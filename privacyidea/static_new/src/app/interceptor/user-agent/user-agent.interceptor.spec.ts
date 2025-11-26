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

import { userAgentInterceptor } from "./user-agent.interceptor";
import { VersioningService, VersioningServiceInterface } from "../../services/version/version.service";
import { HttpEvent, HttpHeaders, HttpRequest } from "@angular/common/http";
import { TestBed } from "@angular/core/testing";
import { Observable } from "rxjs";

describe("userAgentInterceptor", () => {

  const run = (req: HttpRequest<any>, next: (req: HttpRequest<any>) => Observable<HttpEvent<any>>) =>
    TestBed.runInInjectionContext(() => userAgentInterceptor(req, next));


  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [{ provide: VersioningService, useClass: VersioningService }]
    });

    let versioningService: VersioningServiceInterface = TestBed.inject(VersioningService);
    versioningService.version.set("1.2.3");
  });

  it("should add the User-Agent header with the correct version", (done) => {
    const req = new HttpRequest("GET", "/test");
    const next = (request: HttpRequest<any>) => {
      expect(request.headers.get("User-Agent")).toBe("privacyIDEA-WebUI/1.2.3");
      done();
      return null as any;
    };
    run(req, next);
  });

  it("should preserve other headers", (done) => {
    const req = new HttpRequest("GET", "/test", {
      headers: new HttpHeaders({ "PI-Authorization": "abc" })
    } as any);
    const next = (request: HttpRequest<any>) => {
      expect(request.headers.get("PI-Authorization")).toBe("abc");
      expect(request.headers.get("User-Agent")).toBe("privacyIDEA-WebUI/1.2.3");
      done();
      return null as any;
    };
    run(req, next);
  });
});
