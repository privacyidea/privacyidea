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
import { TestBed } from "@angular/core/testing";
import { NavigationEnd, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { Subject } from "rxjs";
import { ContentService } from "./content.service";

describe("ContentService", () => {
  let service: ContentService;

  let events$: Subject<NavigationEnd>;
  let mockRouter: {
    url: string;
    events: any;
    navigateByUrl: jest.Mock<Promise<boolean>, [string]>;
  };

  const emitNav = (url: string) => {
    mockRouter.url = url;
    events$.next(new NavigationEnd(Date.now(), url, url));
  };

  beforeEach(() => {
    events$ = new Subject<NavigationEnd>();
    mockRouter = {
      url: "/start",
      events: events$.asObservable(),
      navigateByUrl: jest.fn(async (url: string) => {
        emitNav(url);
        return true;
      })
    };

    TestBed.configureTestingModule({
      providers: [provideHttpClient(), ContentService, { provide: Router, useValue: mockRouter }]
    });

    service = TestBed.inject(ContentService);
  });

  it("creates the service", () => {
    expect(service).toBeTruthy();
  });

  it("initial routeUrl/previousUrl mirror the starting router.url", () => {
    expect(service.routeUrl()).toBe("/start");
    expect(service.previousUrl()).toBe("/start");
  });

  it("updates routeUrl and previousUrl on NavigationEnd events", () => {
    emitNav("/first");
    expect(service.previousUrl()).toBe("/start");
    expect(service.routeUrl()).toBe("/first");

    emitNav("/second");
    expect(service.previousUrl()).toBe("/first");
    expect(service.routeUrl()).toBe("/second");
  });

  it("onTokenEnrollmentLikely is true for enrollment related routes", () => {
    expect(service.onTokenEnrollmentLikely()).toBe(false);

    emitNav(ROUTE_PATHS.TOKENS_ENROLLMENT);
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.TOKENS_WIZARD);
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.TOKENS_DETAILS + "/SER1");
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.TOKENS);
    expect(service.onTokenEnrollmentLikely()).toBe(false);
  });

  describe("container route signals", () => {
    it("onContainersCreate is true for CONTAINERS_CREATE and CONTAINERS_WIZARD paths", () => {
      expect(service.onContainersCreate()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_CREATE);
      expect(service.onContainersCreate()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_WIZARD);
      expect(service.onContainersCreate()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS);
      expect(service.onContainersCreate()).toBe(false);
    });
  });

  describe("template route signals", () => {
    it("onContainersTemplates is true only for exact CONTAINERS_TEMPLATES path", () => {
      expect(service.onContainersTemplates()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
      expect(service.onContainersTemplates()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES + "/something");
      expect(service.onContainersTemplates()).toBe(false);
    });

    it("onContainersTemplatesCreate is true only for exact CONTAINERS_TEMPLATES_CREATE path", () => {
      expect(service.onContainersTemplatesCreate()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE);
      expect(service.onContainersTemplatesCreate()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
      expect(service.onContainersTemplatesCreate()).toBe(false);
    });

    it("onContainersTemplatesDetails is true for paths starting with CONTAINERS_TEMPLATES_DETAILS", () => {
      expect(service.onContainersTemplatesDetails()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS + "myTemplate");
      expect(service.onContainersTemplatesDetails()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
      expect(service.onContainersTemplatesDetails()).toBe(false);
    });
  });

  describe("tokenSelected()", () => {
    it("navigates to token details and sets serial", async () => {
      emitNav("/containers");
      service.tokenSelected("SER1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_DETAILS + "SER1");
      expect(service.tokenSerial()).toBe("SER1");
      expect(service.routeUrl()).toBe(ROUTE_PATHS.TOKENS_DETAILS + "SER1");
      expect(service.previousUrl()).toBe("/containers");
    });
  });

  describe("containerSelected()", () => {
    it("navigates to container details and sets serial", async () => {
      emitNav("/tokens");
      service.navigateContainerDetails("C1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_DETAILS + "C1");
      expect(service.containerSerial()).toBe("C1");
      expect(service.routeUrl()).toBe(ROUTE_PATHS.CONTAINERS_DETAILS + "C1");
      expect(service.previousUrl()).toBe("/tokens");
    });
  });
});
