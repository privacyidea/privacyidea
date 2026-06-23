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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { Subscription, SubscriptionService } from "@services/subscription/subscription.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of } from "rxjs";
import { SubscriptionsWidgetComponent } from "./subscriptions-widget.component";

const MOCK_SUBSCRIPTION: Subscription = {
  application: "privacyIDEA",
  timedelta: 365,
  level: "Gold",
  num_users: 1000,
  active_users: 42,
  num_tokens: 2000,
  active_tokens: 84,
  num_clients: 10,
  date_from: "2025-01-01",
  date_till: "2026-12-31",
  for_name: "Test Org",
  for_email: "test@example.com",
  for_address: "Test Address",
  for_phone: "123",
  for_url: "https://example.com",
  for_comment: "",
  by_name: "NetKnights",
  by_url: "https://netknights.it",
  by_address: "NetKnights Address",
  by_email: "info@netknights.it",
  by_phone: "456"
};

describe("SubscriptionsWidgetComponent", () => {
  let fixture: ComponentFixture<SubscriptionsWidgetComponent>;
  let component: SubscriptionsWidgetComponent;
  let authMock: MockAuthService;
  let subscriptionMock: MockSubscriptionService;

  const instance: WidgetInstance = { id: "subscriptions-1", type: "subscriptions", x: 0, y: 0, cols: 8, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SubscriptionsWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SubscriptionService, useClass: MockSubscriptionService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["managesubscription"] });

    subscriptionMock = TestBed.inject(SubscriptionService) as unknown as MockSubscriptionService;
    subscriptionMock.getSubscriptions.mockReturnValue(
      of(MockPiResponse.fromValue<Record<string, Subscription>>({ privacyIDEA: MOCK_SUBSCRIPTION }))
    );

    fixture = TestBed.createComponent(SubscriptionsWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(SubscriptionsWidgetComponent.type).toBe("subscriptions");
    expect(SubscriptionsWidgetComponent.title).toBeTruthy();
    expect(SubscriptionsWidgetComponent.icon).toBe("event_repeat");
  });

  it("should override the static size constraints", () => {
    expect(SubscriptionsWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 5 });
    expect(SubscriptionsWidgetComponent.minSize).toEqual({ cols: 8, rows: 5 });
    expect(SubscriptionsWidgetComponent.maxSize).toEqual({ cols: 8, rows: 5 });
  });

  it("should be pinned at a fixed position", () => {
    expect(SubscriptionsWidgetComponent.pinned).toBe(true);
    expect(SubscriptionsWidgetComponent.fixedPosition).toEqual({ x: 16, y: 0 });
  });

  it("should render subscription rows when the right is granted", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("privacyIDEA");
    expect(text).toContain("Gold");
    expect(text).toContain("42/1000");
    expect(text).toContain("2026-12-31");
  });

  it("should render nothing when managesubscription right is missing", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const fixture2 = TestBed.createComponent(SubscriptionsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    fixture2.destroy();
  });
});
