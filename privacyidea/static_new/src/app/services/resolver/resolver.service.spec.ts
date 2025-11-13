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

import { fakeAsync, TestBed, tick } from "@angular/core/testing";
import { Resolver, Resolvers, ResolverService } from "./resolver.service";
import { HttpTestingController, provideHttpClientTesting, TestRequest } from "@angular/common/http/testing";
import { environment } from "../../../environments/environment";
import { HttpHeaders, provideHttpClient } from "@angular/common/http";
import { MockPiResponse } from "../../../testing/mock-services";
import { AuthService } from "../auth/auth.service";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";

describe("ResolverService", () => {
  let resolverService: ResolverService;
  let httpMock: HttpTestingController;
  let authService: MockAuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        ResolverService
      ]
    });
    resolverService = TestBed.inject(ResolverService);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    jest.spyOn(authService, "getHeaders").mockReturnValue(new HttpHeaders({ Authorization: "test-token" }));
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(resolverService).toBeTruthy();
  });

  it("should test a resolver", () => {
    resolverService.postResolverTest().subscribe();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl + "test");
    expect(req.request.method).toBe("POST");
    expect(req.request.headers.get("Authorization")).toBe("test-token");
    req.flush({});
  });

  it("should post a resolver", () => {
    const resolverName = "testResolver";
    const data = { key: "value" };
    resolverService.postResolver(resolverName, data).subscribe();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl + resolverName);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual(data);
    expect(req.request.headers.get("Authorization")).toBe("test-token");
    req.flush({});
  });

  it("should delete a resolver", () => {
    const resolverName = "testResolver";
    resolverService.deleteResolver(resolverName).subscribe();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl + resolverName);
    expect(req.request.method).toBe("DELETE");
    expect(req.request.headers.get("Authorization")).toBe("test-token");
    req.flush({});
  });

  it("should get resolvers", fakeAsync(() => {
    const resolver1: Resolver = {
      censor_keys: [],
      data: {},
      resolvername: "resolver1",
      type: "ldapresolver"
    };
    const resolver2: Resolver = {
      censor_keys: [],
      data: {},
      resolvername: "resolver2",
      type: "ldapresolver"
    };
    const mockResponse = MockPiResponse.fromValue<Resolvers>({
      resolver1,
      resolver2
    });
    TestBed.flushEffects();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(mockResponse);
    tick();
    expect(resolverService.resolvers()).toEqual([resolver1, resolver2]);
  }));

  it("should get resolver options", fakeAsync(() => {
    const resolver1: Resolver = {
      censor_keys: [],
      data: {},
      resolvername: "resolver1",
      type: "ldapresolver"
    };
    const resolver2: Resolver = {
      censor_keys: [],
      data: {},
      resolvername: "resolver2",
      type: "ldapresolver"
    };
    const mockResponse = MockPiResponse.fromValue<Resolvers>({
      resolver1,
      resolver2
    });
    TestBed.flushEffects();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(mockResponse);
    tick();
    expect(resolverService.resolverOptions()).toEqual(["resolver1", "resolver2"]);
  }));
});
