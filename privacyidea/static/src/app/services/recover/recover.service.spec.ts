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
import { environment } from "@env/environment";
import { RecoverService } from "./recover.service";

describe("RecoverService", () => {
  let service: RecoverService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(RecoverService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it("posts the user, realm and email to /recover", () => {
    const params = { user: "alice", realm: "realm1", email: "alice@example.com" };
    service.requestRecoveryCode(params).subscribe();

    const req = httpMock.expectOne(`${environment.proxyUrl}/recover`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual(params);
    req.flush({ result: { status: true, value: true } });
  });

  it("posts the user, realm, code and password to /recover/reset", () => {
    const params = { user: "alice", realm: "realm1", recoverycode: "code", password: "secret" };
    service.resetPassword(params).subscribe();

    const req = httpMock.expectOne(`${environment.proxyUrl}/recover/reset`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual(params);
    req.flush({ result: { status: true, value: true } });
  });
});
