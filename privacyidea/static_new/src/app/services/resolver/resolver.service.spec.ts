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

import { TestBed } from "@angular/core/testing";
import { Resolver, Resolvers, ResolverService } from "./resolver.service";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { HttpHeaders, provideHttpClient } from "@angular/common/http";
import { MockPiResponse } from "../../../testing/mock-services";
import { AuthService } from "../auth/auth.service";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { MockContentService } from "../../../testing/mock-services/mock-content-service";
import { ContentService } from "../content/content.service";
import { ROUTE_PATHS } from "../../route_paths";
import { lastValueFrom, of } from "rxjs";

describe("ResolverService", () => {
  let resolverService: ResolverService;
  let httpMock: HttpTestingController;
  let authService: MockAuthService;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        ResolverService
      ]
    });
    resolverService = TestBed.inject(ResolverService);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    jest.spyOn(authService, "getHeaders").mockReturnValue(new HttpHeaders({ Authorization: "test-token" }));
    contentService.routeUrl.set(ROUTE_PATHS.USERS);
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

  it("should get resolvers", async () => {
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
    TestBed.tick();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(mockResponse);
    await lastValueFrom(of({})); // Wait for async updates
    expect(resolverService.resolverResourceValue()).toEqual({ resolver1, resolver2 });
    expect(resolverService.resolvers()).toEqual([resolver1, resolver2]);
  });

  it("should handle http error of resolverResource", async () => {
    TestBed.tick();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
    await lastValueFrom(of({})); // Wait for async updates

    expect(resolverService.resolverResourceValue()).toEqual({});
    expect(resolverService.resolvers()).toEqual([]);
    expect(resolverService.resolverOptions()).toEqual([]);
    expect(resolverService.editableResolvers()).toEqual([]);
  });

  it("should get resolver options", async () => {
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
    TestBed.tick();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(mockResponse);
    await lastValueFrom(of({})); // Wait for async updates

    expect(resolverService.resolverOptions()).toEqual(["resolver1", "resolver2"]);
  });

  it("editableResolvers should return only editable resolvers (case-insensitive)", async () => {
    const mockResolvers = {
      ldap1: { data: { Editable: true }, type: "ldapresolver" },
      ldap2: { data: { editable: "true" }, type: "ldapresolver" },
      ldap3: { data: { EDITABLE: 1 }, type: "ldapresolver" },
      ldap4: { data: { Editable: false }, type: "ldapresolver" },
      sql1: { data: {}, type: "sqlresolver" }
    };
    const mockResponse = MockPiResponse.fromValue(mockResolvers);
    TestBed.tick();
    const req = httpMock.expectOne(resolverService.resolverBaseUrl);
    expect(req.request.method).toBe("GET");
    req.flush(mockResponse);
    await lastValueFrom(of({})); // Wait for async updates

    TestBed.tick();
    expect(resolverService.editableResolvers()).toEqual(["ldap1", "ldap2", "ldap3"]);
  });

  describe("userAttributes signal", () => {
    it("should return attribute keys for ldapresolver  with stringified mapping", async () => {
      const mockResolvers = {
        "ldap/1": { data: { USERINFO: "{ \"surname\": \"sn\", \"givenname\": \"givenName\" }" }, type: "ldapresolver" }
      };
      (resolverService as any).selectedResolverName.set("ldap/1");
      const mockResponse = MockPiResponse.fromValue(mockResolvers);

      TestBed.tick();
      httpMock.expectOne(resolverService.resolverBaseUrl); // accept initial load of all resolvers;
      const req = httpMock.expectOne(resolverService.resolverBaseUrl + encodeURIComponent("ldap/1"));
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      expect(resolverService.userAttributes()).toEqual(["surname", "givenname"]);
    });

    it("should return empty attributes list for invalid JSON string", async () => {
      const mockResolvers = {
        "ldap/1": { data: { USERINFO: "{ 'surname': 'sn', 'givenname': 'givenName' " }, type: "ldapresolver" }
      };
      (resolverService as any).selectedResolverName.set("ldap/1");
      const mockResponse = MockPiResponse.fromValue(mockResolvers);

      TestBed.tick();
      httpMock.expectOne(resolverService.resolverBaseUrl); // accept initial load of all resolvers;
      const req = httpMock.expectOne(resolverService.resolverBaseUrl + encodeURIComponent("ldap/1"));
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      expect(resolverService.userAttributes()).toEqual([]);
    });

    it("should return attribute keys for sqlresolver", async () => {
      const mockResolvers = {
        "sql/1": { data: { Map: { givenname: "displayname", email: "mail" } }, type: "sqlresolver" }
      };
      const mockResponse = MockPiResponse.fromValue(mockResolvers);
      (resolverService as any).selectedResolverName.set("sql/1");

      TestBed.tick();
      httpMock.expectOne(resolverService.resolverBaseUrl); // accept initial load of all resolvers;
      const req = httpMock.expectOne(resolverService.resolverBaseUrl + encodeURIComponent("sql/1"));
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      expect(resolverService.userAttributes()).toEqual(["givenname", "email"]);
    });

    it("should return attribute keys for httpresolver", async () => {
      const mockResolvers = {
        http1: {
          data: {
            attribute_mapping: {
              username: "userPrincipalName",
              mobile: "mobilePhone",
              surname: "surname"
            }
          }, type: "httpresolver"
        }
      };
      const mockResponse = MockPiResponse.fromValue(mockResolvers);
      (resolverService as any).selectedResolverName.set("http1");

      TestBed.tick();
      httpMock.expectOne(resolverService.resolverBaseUrl); // accept initial load of all resolvers;
      const req = httpMock.expectOne(resolverService.resolverBaseUrl + "http1");
      expect(req.request.method).toBe("GET");
      req.flush(mockResponse);
      await lastValueFrom(of({})); // Wait for async updates

      expect(resolverService.userAttributes()).toEqual(["username", "mobile", "surname"]);
    });

    it("should return empty array if no resolver resource is loaded", () => {
      expect(resolverService.userAttributes()).toEqual([]);
    });
  });
});
