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
import { RealmService } from "./realm.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { ROUTE_PATHS } from "../../route_paths";
import {
  MockAuthService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "../../../testing/mock-services";

describe("RealmService", () => {
  let realmService: RealmService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        RealmService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        MockNotificationService,
        MockLocalService
      ]
    });

    realmService = TestBed.inject(RealmService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(realmService).toBeTruthy();
  });

  it("createRealm for global realm sends resolver names and only priorities that are set", () => {
    const realmName = "my realm";
    const resolvers = [
      { name: "res1", priority: 10 },
      { name: "res2", priority: null },
      { name: "res3" } as any
    ];

    realmService.createRealm(realmName, "", resolvers).subscribe();

    const req = httpMock.expectOne(
      `${environment.proxyUrl}/realm/${encodeURIComponent(realmName)}`
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      resolvers: ["res1", "res2", "res3"],
      "priority.res1": 10
    });
    expect(req.request.body["priority.res2"]).toBeUndefined();
    expect(req.request.body["priority.res3"]).toBeUndefined();

    req.flush({ result: "ok" });
  });

  it("createRealm for global realm ignores non-numeric priority values", () => {
    const realmName = "realm";
    const resolvers = [
      { name: "res1", priority: "not-a-number" as any }
    ];

    realmService.createRealm(realmName, "", resolvers).subscribe();

    const req = httpMock.expectOne(
      `${environment.proxyUrl}/realm/${encodeURIComponent(realmName)}`
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      resolvers: ["res1"]
    });
    expect(req.request.body["priority.res1"]).toBeUndefined();

    req.flush({ result: "ok" });
  });

  it("createRealm for node-specific realm sends resolver objects with optional priority", () => {
    const realmName = "node realm";
    const nodeId = "node-1";
    const resolvers = [
      { name: "res1", priority: null },
      { name: "res2", priority: 5 },
      { name: "res3" } as any
    ];

    realmService.createRealm(realmName, nodeId, resolvers).subscribe();

    const req = httpMock.expectOne(
      `${environment.proxyUrl}/realm/${encodeURIComponent(realmName)}/node/${nodeId}`
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      resolver: [
        { name: "res1" },
        { name: "res2", priority: 5 },
        { name: "res3" }
      ]
    });

    req.flush({ result: "ok" });
  });

  it("createRealm for node-specific realm ignores non-numeric priority values", () => {
    const realmName = "realm-node";
    const nodeId = "node-2";
    const resolvers = [
      { name: "res1", priority: "7" as any },
      { name: "res2", priority: "not-a-number" as any }
    ];

    realmService.createRealm(realmName, nodeId, resolvers).subscribe();

    const req = httpMock.expectOne(
      `${environment.proxyUrl}/realm/${encodeURIComponent(realmName)}/node/${nodeId}`
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      resolver: [
        { name: "res1", priority: 7 },
        { name: "res2" }
      ]
    });

    req.flush({ result: "ok" });
  });

  it("deleteRealm sends DELETE to encoded realm URL", () => {
    const realmName = "realm with space/ä";
    realmService.deleteRealm(realmName).subscribe();

    const req = httpMock.expectOne(
      `${environment.proxyUrl}/realm/${encodeURIComponent(realmName)}`
    );
    expect(req.request.method).toBe("DELETE");

    req.flush({ result: 1 });
  });

  it("setDefaultRealm sends POST to encoded defaultrealm URL with empty body", () => {
    const realmName = "default realm/ä";
    realmService.setDefaultRealm(realmName).subscribe();

    const req = httpMock.expectOne(
      `${environment.proxyUrl}/defaultrealm/${encodeURIComponent(realmName)}`
    );
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({});

    req.flush({ result: 1 });
  });
});
