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
import { MatDialog } from "@angular/material/dialog";
import { AuthService } from "@services/auth/auth.service";
import { MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { SubscriptionExpiryService } from "./subscription-expiry.service";
import { Subscription, SubscriptionService } from "./subscription.service";

function makeSubs(value: Record<string, Partial<Subscription>>) {
  return MockPiResponse.fromValue<Record<string, Subscription>>(value as Record<string, Subscription>);
}

describe("SubscriptionExpiryService", () => {
  let dialogMock: { open: jest.Mock };
  let authMock: MockAuthService;
  let subsMock: MockSubscriptionService;

  beforeEach(() => {
    dialogMock = { open: jest.fn() };

    TestBed.configureTestingModule({
      providers: [
        SubscriptionExpiryService,
        { provide: MatDialog, useValue: dialogMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SubscriptionService, useClass: MockSubscriptionService }
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    subsMock = TestBed.inject(SubscriptionService) as unknown as MockSubscriptionService;
    authMock.isAuthenticated.set(false);
  });

  it("opens dialog with expiring subscriptions when authenticated", () => {
    subsMock.subscriptionsResource.set(
      makeSubs({
        a: { application: "app1", timedelta: -10, date_till: "2026-02-01" },
        b: { application: "app2", timedelta: -40, date_till: "2026-01-01" }
      })
    );
    authMock.isAuthenticated.set(true);

    const service = TestBed.inject(SubscriptionExpiryService);

    TestBed.tick();

    expect(service.opened()).toBe(true);
    expect(dialogMock.open).toHaveBeenCalled();

    const [, config] = dialogMock.open.mock.calls[0];
    // expect(config.data.items.length).toBe(1);
    expect(config.data.items[0].application).toBe("app1");
  });

  it("does not open when no expiring items", () => {
    subsMock.subscriptionsResource.set(
      makeSubs({
        a: { application: "app1", timedelta: -40, date_till: "2026-01-01" },
        b: { application: "app2", timedelta: 5, date_till: "2026-03-01" }
      })
    );
    authMock.isAuthenticated.set(true);

    const service = TestBed.inject(SubscriptionExpiryService);

    expect(service.opened()).toBe(false);
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it("opens only once per session even if data changes again", () => {
    subsMock.subscriptionsResource.set(makeSubs({ a: { application: "app1", timedelta: -5, date_till: "d" } }));
    authMock.isAuthenticated.set(true);

    TestBed.inject(SubscriptionExpiryService);
    TestBed.tick();

    expect(dialogMock.open).toHaveBeenCalledTimes(1);

    subsMock.subscriptionsResource.set(makeSubs({ a: { application: "app1", timedelta: -6, date_till: "d" } }));
    TestBed.tick();

    expect(dialogMock.open).toHaveBeenCalledTimes(1);
  });
});
