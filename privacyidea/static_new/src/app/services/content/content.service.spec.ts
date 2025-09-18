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
import { provideHttpClient } from "@angular/common/http";
import { ContentService } from "./content.service";
import { ROUTE_PATHS } from "../../route_paths";
import { NavigationEnd, Router } from "@angular/router";
import { Subject } from "rxjs";

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
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: mockRouter }
      ]
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

  describe("tokenSelected()", () => {
    it("navigates to token details, sets serial, and marks programmatic change when coming from containers", async () => {
      emitNav("/tokens/containers");

      expect(service.isProgrammaticTabChange()).toBe(false);

      service.tokenSelected("SER1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(
        ROUTE_PATHS.TOKENS_DETAILS + "SER1"
      );
      expect(service.tokenSerial()).toBe("SER1");
      expect(service.isProgrammaticTabChange()).toBe(true);

      expect(service.routeUrl()).toBe(ROUTE_PATHS.TOKENS_DETAILS + "SER1");
      expect(service.previousUrl()).toBe("/tokens/containers");
    });
  });

  describe("containerSelected()", () => {
    it("navigates to container details, sets serial, and marks programmatic change when not on containers route", async () => {
      emitNav("/tokens");
      expect(service.isProgrammaticTabChange()).toBe(false);

      service.containerSelected("C1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(
        ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "C1"
      );
      expect(service.containerSerial()).toBe("C1");
      expect(service.isProgrammaticTabChange()).toBe(true);

      expect(service.routeUrl()).toBe(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "C1");
      expect(service.previousUrl()).toBe("/tokens");
    });

    it("does NOT mark programmatic change when already on containers route", async () => {
      emitNav("/tokens/containers");
      service.isProgrammaticTabChange.set(false);

      service.containerSelected("C2");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(
        ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "C2"
      );
      expect(service.containerSerial()).toBe("C2");
      expect(service.isProgrammaticTabChange()).toBe(false);
    });
  });
});