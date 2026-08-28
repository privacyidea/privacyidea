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
import { LOCALE_ID, provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { IntegrationsService } from "@services/integrations/integrations.service";
import { SubscriptionService, SubscriptionStatus } from "@services/subscription/subscription.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockIntegrationsService } from "@testing/mock-services/mock-integrations-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, Subject } from "rxjs";
import { SubscriptionsWidgetComponent } from "./subscriptions-widget.component";

function status(overrides: Partial<SubscriptionStatus> & { application: string }): SubscriptionStatus {
  return {
    is_server: false,
    in_use: false,
    subscription: "none",
    last_seen: null,
    date_till: null,
    days_left: null,
    versions: [],
    current_version: null,
    current_version_date: null,
    current_version_url: null,
    ...overrides
  };
}

const SERVER_STATUS = status({
  application: "privacyidea",
  is_server: true,
  in_use: true,
  subscription: "expiring",
  date_till: "Wed, 31 Dec 2026 00:00:00 GMT",
  days_left: 41,
  versions: ["3.13.1"],
  current_version: "3.14.0",
  current_version_date: "2026-08-01",
  current_version_url: null
});

const APP_STATUS = status({
  application: "privacyidea-app",
  in_use: true,
  subscription: "valid",
  last_seen: "Mon, 17 Aug 2026 09:00:00 GMT",
  date_till: "Fri, 31 Dec 2027 00:00:00 GMT",
  days_left: 500,
  versions: ["4.5.0", "4.4.1"],
  current_version: "4.6.0",
  current_version_date: "2026-07-20",
  current_version_url: null
});

const KEYCLOAK_STATUS = status({
  application: "privacyidea-keycloak",
  in_use: true,
  subscription: "exceeded",
  date_till: "Sat, 30 Jun 2029 00:00:00 GMT",
  days_left: 1048,
  current_version: "1.6.0",
  current_version_date: "2026-06-01",
  current_version_url: "https://github.com/privacyidea/keycloak-provider/releases/tag/v1.6.0"
});

describe("SubscriptionsWidgetComponent", () => {
  let fixture: ComponentFixture<SubscriptionsWidgetComponent>;
  let component: SubscriptionsWidgetComponent;
  let authMock: MockAuthService;
  let subscriptionMock: MockSubscriptionService;

  const instance: WidgetInstance = { id: "subscriptions-1", type: "subscriptions", x: 0, y: 0, cols: 8, rows: 5 };

  const createWidget = (): ComponentFixture<SubscriptionsWidgetComponent> => {
    const created = TestBed.createComponent(SubscriptionsWidgetComponent);
    created.componentRef.setInput("instance", instance);
    created.detectChanges();
    return created;
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SubscriptionsWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SubscriptionService, useClass: MockSubscriptionService },
        { provide: IntegrationsService, useClass: MockIntegrationsService },
        { provide: LOCALE_ID, useValue: "en" }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["managesubscription"] });

    subscriptionMock = TestBed.inject(SubscriptionService) as unknown as MockSubscriptionService;
    subscriptionMock.getSubscriptionStatus.mockReturnValue(
      of(MockPiResponse.fromValue<SubscriptionStatus[]>([SERVER_STATUS, APP_STATUS, KEYCLOAK_STATUS]))
    );

    fixture = createWidget();
    component = fixture.componentInstance;
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

  it("should be an ordinary widget the admin can move, resize and remove", () => {
    expect(SubscriptionsWidgetComponent.pinned).toBe(false);
    expect(SubscriptionsWidgetComponent.fixedPosition).toBeNull();
    // Opens tall enough for the compact view to show every component without scrolling.
    expect(SubscriptionsWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 11 });
    expect(SubscriptionsWidgetComponent.minSize.cols).toBeLessThan(SubscriptionsWidgetComponent.defaultSize.cols);
    expect(SubscriptionsWidgetComponent.maxSize.cols).toBeGreaterThan(SubscriptionsWidgetComponent.defaultSize.cols);
  });

  it("should render the server row first, then the sectioned components", () => {
    const rows = component.rows();

    expect(rows[0].kind).toBe("server");
    expect(rows[0].status?.application).toBe("privacyidea");
    expect(rows.filter((row) => row.kind === "label").map((row) => row.label)).toEqual([
      "Use Cases",
      "System Login",
      "Single Sign On"
    ]);
    expect(rows.filter((row) => row.kind === "component").map((row) => row.application)).toEqual([
      "privacyidea-app",
      "freeradius",
      "privacyidea-nextcloud",
      "privacyidea-cp",
      "pam",
      "pam-passkey",
      "privacyidea-keycloak",
      "entraid-via-keycloak",
      "privacyidea-adfs",
      "privacyidea-shibboleth"
    ]);
  });

  it("should indent every section label at the top level and every component one level in", () => {
    const rows = component.rows();

    expect(rows.filter((row) => row.kind === "label").every((row) => row.indent === 0)).toBe(true);
    expect(rows.filter((row) => row.kind === "component").every((row) => row.indent === 1)).toBe(true);
  });

  it("should fall back to the raw section key when the catalog reports an unrecognized section", () => {
    const integrationsMock = TestBed.inject(IntegrationsService) as unknown as MockIntegrationsService;
    integrationsMock.integrations.update((integrations) =>
      integrations.map((integration) =>
        integration.id === "freeradius" ? { ...integration, section: "some_future_section" } : integration
      )
    );
    fixture = createWidget();
    component = fixture.componentInstance;

    const rows = component.rows();

    expect(rows.filter((row) => row.kind === "label").map((row) => row.label)).toContain("some_future_section");
  });

  it("should fall back to an unused status for components the backend did not report", () => {
    const radius = component.rows().find((row) => row.application === "freeradius");

    expect(radius?.status).toEqual(
      expect.objectContaining({ application: "freeradius", in_use: false, subscription: "none" })
    );
  });

  it("should render the display names instead of the raw application keys", () => {
    const text = fixture.nativeElement.textContent;

    expect(text).toContain("privacyIDEA Server");
    expect(text).toContain("FreeRADIUS");
    expect(text).toContain("Nextcloud");
    expect(text).toContain("PAM Passkey");
    expect(text).not.toContain("privacyidea-cp");
  });

  it("should show a status dot per axis in the compact view", () => {
    const headers = Array.from(fixture.nativeElement.querySelectorAll("th")).map((th) =>
      (th as HTMLElement).textContent?.trim()
    );

    expect(headers).toEqual(["Application", "Usage", "Subscription"]);
    expect(fixture.nativeElement.querySelectorAll(".status-dot").length).toBe(11 * 2);
  });

  it("should colour the dots by usage and subscription state", () => {
    const serverRow = fixture.nativeElement.querySelector("tbody tr");
    const dots = serverRow.querySelectorAll(".status-dot");

    // The server is in use and its subscription is expiring.
    expect(dots[0].classList).toContain("dot-good");
    expect(dots[1].classList).toContain("dot-warn");
  });

  it("should give every dot a glyph and a name, so the colour is not the only channel", () => {
    const rows: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll("tbody tr"));
    const dotsOf = (name: string): HTMLElement[] =>
      Array.from(
        rows
          .find((row) => row.querySelector(".application-cell")?.textContent?.includes(name))!
          .querySelectorAll(".status-dot")
      );

    // In use and expiring: the two dots differ in glyph as well as in hue.
    const [serverUsage, serverSubscription] = dotsOf("privacyIDEA Server");
    expect(serverUsage.textContent!.trim()).toBe("\u2713");
    expect(serverSubscription.textContent!.trim()).toBe("!");

    // Not in use and no subscription: red against grey, again told apart by the glyph.
    const [radiusUsage, radiusSubscription] = dotsOf("FreeRADIUS");
    expect(radiusUsage.textContent!.trim()).toBe("\u2715");
    expect(radiusSubscription.textContent!.trim()).toBe("\u2013");

    // The reason is the cell's accessible name, not only its tooltip: the dot itself is
    // hidden from assistive technology.
    const cells: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll(".status-cell"));
    expect(cells.length).toBe(11 * 2);
    for (const cell of cells) {
      expect(cell.getAttribute("role")).toBe("img");
      expect(cell.getAttribute("aria-label")).toBeTruthy();
    }
    expect(cells[0].getAttribute("aria-label")).toBe("In use: this is the privacyIDEA server itself.");
  });

  it("should trade the status dots for the dates and versions when toggled to detailed", () => {
    component.toggleDetailed();
    fixture.detectChanges();

    const headers = Array.from(fixture.nativeElement.querySelectorAll("th")).map((th) =>
      (th as HTMLElement).textContent?.trim()
    );
    expect(headers).toEqual(["Application", "Expires", "Versions", "Current version"]);
    // The dots would only repeat what the expiry column already shows.
    expect(fixture.nativeElement.querySelector(".status-dot")).toBeNull();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain("2026-12-31");
    expect(text).toContain("4.5.0, 4.4.1");
    expect(text).toContain("3.14.0");
  });

  it("should name the subscription state next to the expiry date", () => {
    component.toggleDetailed();
    fixture.detectChanges();

    const rows: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll("tbody tr"));
    const expiryOf = (name: string): string =>
      rows
        .find((row) => row.querySelector(".application-cell")?.textContent?.includes(name))!
        .querySelector(".expires-cell")!
        .textContent!.replace(/\s+/g, " ")
        .trim();

    expect(expiryOf("privacyIDEA Server")).toBe("2026-12-31 (expiring, 41 days left)");
    expect(expiryOf("privacyIDEA Authenticator App")).toBe("2027-12-31 (valid, 500 days left)");
    // The state a date alone could never show.
    expect(expiryOf("Keycloak")).toBe("2029-06-30 (exceeded, 1048 days left)");
    // No subscription, no date: nothing to qualify.
    expect(expiryOf("FreeRADIUS")).toBe("—");
  });

  it("should count a passed expiry date as days ago", () => {
    subscriptionMock.getSubscriptionStatus.mockReturnValue(
      of(
        MockPiResponse.fromValue<SubscriptionStatus[]>([
          status({
            application: "privacyidea",
            is_server: true,
            in_use: true,
            subscription: "expired",
            date_till: "Tue, 30 Jun 2026 00:00:00 GMT",
            days_left: -49
          })
        ])
      )
    );
    TestBed.inject(DashboardDataStore).invalidate();

    const expired = createWidget();
    expired.componentInstance.toggleDetailed();
    expired.detectChanges();

    const serverExpiry = expired.nativeElement.querySelector("tbody tr .expires-cell");
    expect(serverExpiry.textContent.replace(/\s+/g, " ").trim()).toBe("2026-06-30 (expired, 49 days ago)");
    expired.destroy();
  });

  it("should call the expiry day today rather than counting zero days", () => {
    subscriptionMock.getSubscriptionStatus.mockReturnValue(
      of(
        MockPiResponse.fromValue<SubscriptionStatus[]>([
          status({
            application: "privacyidea",
            is_server: true,
            in_use: true,
            subscription: "expired",
            date_till: "Tue, 30 Jun 2026 00:00:00 GMT",
            days_left: 0
          })
        ])
      )
    );
    TestBed.inject(DashboardDataStore).invalidate();

    const today = createWidget();
    today.componentInstance.toggleDetailed();
    today.detectChanges();

    const serverExpiry = today.nativeElement.querySelector("tbody tr .expires-cell");
    expect(serverExpiry.textContent.replace(/\s+/g, " ").trim()).toBe("2026-06-30 (expired, today)");
    today.destroy();
  });

  it("should link a component with a subscription to the sla page and one without to non-sla", () => {
    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a[href]"));
    const hrefByName = new Map(links.map((link) => [link.textContent?.trim(), link.getAttribute("href")]));

    expect(hrefByName.get("privacyIDEA Authenticator App")).toBe(
      "https://netknights.it/plugin-traffic-light/en/sla/privacyidea-authenticator-app"
    );
    expect(hrefByName.get("FreeRADIUS")).toBe(
      "https://netknights.it/plugin-traffic-light/en/non-sla/privacyidea-freeradius"
    );
  });

  it("should keep an exceeded subscription on the sla page", () => {
    // Exceeded means the subscription still covers the component, just not enough users.
    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a[href]"));
    const keycloak = links.find((link) => link.textContent?.trim() === "Keycloak");

    expect(keycloak?.getAttribute("href")).toBe(
      "https://netknights.it/plugin-traffic-light/en/sla/privacyidea-keycloak"
    );
  });

  it("should send an expired subscription to its own landing page", () => {
    subscriptionMock.getSubscriptionStatus.mockReturnValue(
      of(
        MockPiResponse.fromValue<SubscriptionStatus[]>([
          status({
            application: "privacyidea-keycloak",
            in_use: true,
            subscription: "expired",
            date_till: "Tue, 30 Jun 2026 00:00:00 GMT",
            days_left: -49
          })
        ])
      )
    );
    TestBed.inject(DashboardDataStore).invalidate();

    const expired = createWidget();
    const links: HTMLAnchorElement[] = Array.from(expired.nativeElement.querySelectorAll("a[href]"));
    const keycloak = links.find((link) => link.textContent?.trim() === "Keycloak");

    expect(keycloak?.getAttribute("href")).toBe(
      "https://netknights.it/plugin-traffic-light/en/expired/privacyidea-keycloak"
    );
    expired.destroy();
  });

  it("should use the German landing pages when the German bundle is served", () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [SubscriptionsWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SubscriptionService, useClass: MockSubscriptionService },
        { provide: IntegrationsService, useClass: MockIntegrationsService },
        { provide: LOCALE_ID, useValue: "de" }
      ]
    });
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["managesubscription"]
    });
    (TestBed.inject(SubscriptionService) as unknown as MockSubscriptionService).getSubscriptionStatus.mockReturnValue(
      of(MockPiResponse.fromValue<SubscriptionStatus[]>([SERVER_STATUS, APP_STATUS]))
    );

    const germanFixture = createWidget();
    const links: HTMLAnchorElement[] = Array.from(germanFixture.nativeElement.querySelectorAll("a[href]"));
    const app = links.find((link) => link.textContent?.trim() === "privacyIDEA Authenticator App");

    expect(app?.getAttribute("href")).toBe(
      "https://netknights.it/plugin-traffic-light/de/sla/privacyidea-authenticator-app"
    );
    germanFixture.destroy();
  });

  it("should keep a version list in its own cell container with the full list on hover", () => {
    component.toggleDetailed();
    fixture.detectChanges();

    // The container is what stays one line high and scrolls, instead of the list
    // wrapping and making every row taller.
    const rows: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll("tbody tr"));
    const rowOf = (name: string): HTMLElement =>
      rows.find((row) => row.querySelector(".application-cell")?.textContent?.includes(name))!;

    const appVersions = rowOf("privacyIDEA Authenticator App").querySelector(".versions-cell")!;
    expect(appVersions.querySelector(".versions-scroll")?.textContent?.trim()).toBe("4.5.0, 4.4.1");

    // Components without versions render a placeholder, not an empty scroll container.
    const radiusVersions = rowOf("FreeRADIUS").querySelector(".versions-cell")!;
    expect(radiusVersions.querySelector(".versions-scroll")).toBeNull();
    expect(radiusVersions.textContent?.trim()).toBe("—");
  });

  it("should link the current version to its release page when one is known", () => {
    component.toggleDetailed();
    fixture.detectChanges();

    const releaseLink = fixture.nativeElement.querySelector(
      'a[href="https://github.com/privacyidea/keycloak-provider/releases/tag/v1.6.0"]'
    );
    expect(releaseLink.textContent.trim()).toBe("1.6.0");
  });

  it("should offer the status of every row except the section headers as JSON", () => {
    const copied = JSON.parse(component.statusJson());

    expect(copied).toHaveLength(11);
    expect(copied[0]).toEqual(expect.objectContaining({ application: "privacyidea", is_server: true }));
    expect(copied.some((entry: SubscriptionStatus) => entry.application === "privacyidea-nextcloud")).toBe(true);
  });

  it("should keep both status axes in the JSON, which the detailed view no longer shows", () => {
    component.toggleDetailed();
    fixture.detectChanges();

    const copied: SubscriptionStatus[] = JSON.parse(component.statusJson());

    expect(copied.every((entry) => typeof entry.in_use === "boolean")).toBe(true);
    expect(copied.every((entry) => typeof entry.subscription === "string")).toBe(true);
    expect(copied.find((entry) => entry.application === "privacyidea-keycloak")).toEqual(
      expect.objectContaining({ in_use: true, subscription: "exceeded" })
    );
  });

  it("should deny the widget when the managesubscription right is missing", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const denied = createWidget();

    expect(denied.componentInstance.state()).toBe("denied");
    expect(denied.nativeElement.querySelector("table")).toBeNull();
    denied.destroy();
  });

  it("should set the state to loading while the request is still in flight", () => {
    TestBed.inject(DashboardDataStore).invalidate();
    subscriptionMock.getSubscriptionStatus.mockReturnValue(new Subject<MockPiResponse<SubscriptionStatus[]>>());

    const loading = createWidget();

    expect(loading.componentInstance.state()).toBe("loading");
    loading.destroy();
  });

  it("should set the state to error when the request fails", () => {
    TestBed.inject(DashboardDataStore).invalidate();
    const subject = new Subject<MockPiResponse<SubscriptionStatus[]>>();
    subscriptionMock.getSubscriptionStatus.mockReturnValue(subject);

    const failing = createWidget();
    subject.error(new Error("boom"));
    failing.detectChanges();

    expect(failing.componentInstance.state()).toBe("error");
    failing.destroy();
  });

  it("should invalidate the cache and reload on reload()", () => {
    subscriptionMock.getSubscriptionStatus.mockClear();

    component.reload();

    expect(subscriptionMock.getSubscriptionStatus).toHaveBeenCalledTimes(1);
  });
});
