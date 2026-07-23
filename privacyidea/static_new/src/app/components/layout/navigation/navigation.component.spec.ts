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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideLocationMocks } from "@angular/common/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSnackBar } from "@angular/material/snack-bar";
import { provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { NavItem, NavigationComponent } from "@components/layout/navigation/navigation.component";
import { AuthService } from "@services/auth/auth.service";
import { ConfigService } from "@services/config/config.service";
import { ContentService } from "@services/content/content.service";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { NotificationService } from "@services/notification/notification.service";
import { SessionTimerService } from "@services/session-timer/session-timer.service";
import { UserService } from "@services/user/user.service";
import { VersioningService } from "@services/version/version.service";
import { MockConfigService } from "@testing/mock-services/mock-config-service";
import {
  MockContentService,
  MockDocumentationService,
  MockLocalService,
  MockNotificationService,
  MockPeriodicTaskService,
  MockRealmService,
  MockSessionTimerService,
  MockSystemService,
  MockUserService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { RealmService } from "@services/realm/realm.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { EventService } from "@services/event/event.service";
import { SystemService } from "@services/system/system.service";

interface NavigationComponentPrivate {
  getFilteredNavItems: () => NavItem[];
  calculateVisibleItems: (navEl: HTMLElement) => void;
}

describe("NavigationComponent (async, no RouterTestingModule, no MatSnackBar)", () => {
  let component: NavigationComponent;
  let fixture: ComponentFixture<NavigationComponent>;

  beforeAll(async () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });
  });

  afterAll(() => {
    (console.error as jest.Mock)?.mockRestore?.();
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavigationComponent],
      providers: [
        provideRouter([]),
        provideLocationMocks(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: UserService, useClass: MockUserService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SessionTimerService, useClass: MockSessionTimerService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ConfigService, useClass: MockConfigService },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
        { provide: RealmService, useClass: MockRealmService },
        { provide: DocumentationService, useClass: MockDocumentationService },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: EventService, useClass: MockEventService },
        { provide: SystemService, UseClass: MockSystemService },
        PendingChangesService,
        MockLocalService
      ]
    })
      .overrideComponent(NavigationComponent, { set: { template: "" } })
      .compileComponents();

    fixture = TestBed.createComponent(NavigationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should move the active item from overflow to visible list", () => {
    const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    (authService.actionAllowed as jest.Mock).mockReturnValue(true);

    // Set active section to "logs" (index 6 in primaryNavItems)
    contentService.routeUrl.set(ROUTE_PATHS.AUDIT);

    // Set visible count to 3
    component.visibleNavCount.set(3);

    const visible = component.visibleNavItems;
    const overflow = component.overflowNavItems;

    // Total filtered items = 9 (assuming all are allowed in MockAuthService)
    // Audit is at index 6. 6 >= 3 is true.
    // Visible should be [items[0], items[1], items[6]]
    expect(visible.length).toBe(3);
    expect(visible[2].section).toBe("logs");

    // Overflow should contain items that were displaced or were already there
    // Indices: 2, 3, 5, 7, 8 (users, policies, subscription, external, config)
    expect(overflow.length).toBe(5);
    expect(overflow.some((item) => item.section === "logs")).toBe(false);
    expect(overflow[0].section).toBe("users");
  });

  it("should return false for isOverflowSectionActive when the active item is moved to visible list", () => {
    const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    (authService.actionAllowed as jest.Mock).mockReturnValue(true);

    contentService.routeUrl.set(ROUTE_PATHS.AUDIT);
    component.visibleNavCount.set(3);

    expect(component.isOverflowSectionActive()).toBe(false);
  });

  it("should account for padding and gap when calculating visible items", () => {
    const navEl = document.createElement("div");
    Object.defineProperty(navEl, "clientWidth", { value: 300, configurable: true });

    const item1 = document.createElement("div");
    item1.className = "nav-item";
    item1.setAttribute("data-section", "token");
    Object.defineProperty(item1, "offsetWidth", { value: 100, configurable: true });

    const item2 = document.createElement("div");
    item2.className = "nav-item";
    item2.setAttribute("data-section", "container");
    Object.defineProperty(item2, "offsetWidth", { value: 100, configurable: true });

    // Mock the "more" button to avoid using the large default fallback (180)
    const moreBtn = document.createElement("div");
    moreBtn.className = "nav-item";
    const moreBtnInner = document.createElement("button");
    moreBtnInner.className = "more-button";
    moreBtn.appendChild(moreBtnInner);
    Object.defineProperty(moreBtn, "offsetWidth", { value: 50, configurable: true });
    navEl.appendChild(moreBtn);

    navEl.appendChild(item1);
    navEl.appendChild(item2);

    const componentPrivate = component as unknown as NavigationComponentPrivate;
    jest
      .spyOn(componentPrivate, "getFilteredNavItems")
      .mockReturnValue([{ section: "token" }, { section: "container" }] as NavItem[]);

    componentPrivate.calculateVisibleItems(navEl);

    expect(component.visibleNavCount()).toBe(2);

    // Shrink navWidth - should trigger overflow
    // To fit 1 item (100px) with more button (50px) and safety buffer (30px), we need at least 180px.
    Object.defineProperty(navEl, "clientWidth", { value: 200, configurable: true });
    componentPrivate.calculateVisibleItems(navEl);
    // item1(100) fits in availableWidth (200 - 50 - 30 = 120).
    expect(component.visibleNavCount()).toBe(1);
  });

  it("should grow visibleNavCount when space becomes available using stored widths", () => {
    const navEl = document.createElement("div");
    Object.defineProperty(navEl, "clientWidth", { value: 300, configurable: true });

    const item1 = document.createElement("div");
    item1.className = "nav-item";
    item1.setAttribute("data-section", "token");
    Object.defineProperty(item1, "offsetWidth", { value: 100, configurable: true });

    const item2 = document.createElement("div");
    item2.className = "nav-item";
    item2.setAttribute("data-section", "container");
    Object.defineProperty(item2, "offsetWidth", { value: 100, configurable: true });

    navEl.appendChild(item1);
    navEl.appendChild(item2);

    const componentPrivate = component as unknown as NavigationComponentPrivate;
    jest
      .spyOn(componentPrivate, "getFilteredNavItems")
      .mockReturnValue([{ section: "token" }, { section: "container" }] as NavItem[]);

    // Initial calculation to store widths
    componentPrivate.calculateVisibleItems(navEl);
    expect(component.visibleNavCount()).toBe(2);

    // Remove item2 from DOM (simulating Angular removing it from visible items)
    navEl.removeChild(item2);

    // Grow container
    Object.defineProperty(navEl, "clientWidth", { value: 500, configurable: true });
    componentPrivate.calculateVisibleItems(navEl);

    // Should still calculate 2 visible items because it remembers the width of 'container'
    expect(component.visibleNavCount()).toBe(2);
  });

  describe("customLogo and versionPrefix", () => {
    it("should return null for customLogo when no logo is configured", () => {
      const configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
      configService.config.set({ ...configService.config(), logo: "" });

      expect(component.customLogo()).toBeNull();
    });

    it("should build customLogo URL when a logo is configured", () => {
      const configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
      configService.config.set({ ...configService.config(), logo: "my-logo.png" });

      const logo = component.customLogo();
      expect(logo).not.toBeNull();
      expect(logo).toContain("/static/public/my-logo.png");
    });

    it("should return empty versionPrefix when no custom logo is set", () => {
      const configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
      configService.config.set({ ...configService.config(), logo: "" });

      expect(component.versionPrefix()).toBe("");
    });

    it("should return 'privacyIDEA ' versionPrefix when a custom logo is set", () => {
      const configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
      configService.config.set({ ...configService.config(), logo: "my-logo.png" });

      expect(component.versionPrefix()).toBe("privacyIDEA ");
    });

    it("should expose the version from VersioningService", () => {
      const versioningService = TestBed.inject(VersioningService);
      expect(typeof versioningService.version()).toBe("string");
    });
  });

  describe("activeSection", () => {
    let contentService: MockContentService;

    beforeEach(() => {
      contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    });

    it("should default to 'token' for an unknown route", () => {
      contentService.routeUrl.set("/something/else");
      expect(component.activeSection()).toBe("token");
    });

    it("should detect 'container' for containers route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      expect(component.activeSection()).toBe("container");
    });

    it("should detect 'users' for users route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.USERS);
      expect(component.activeSection()).toBe("users");
    });

    it("should detect 'policies' for policies route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.POLICIES);
      expect(component.activeSection()).toBe("policies");
    });

    it("should detect 'subscription' for subscription route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.SUBSCRIPTION);
      expect(component.activeSection()).toBe("subscription");
    });

    it("should detect 'logs' for logs route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.AUDIT);
      expect(component.activeSection()).toBe("logs");
    });

    it("should detect 'external_services' for external services route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
      expect(component.activeSection()).toBe("external_services");
    });

    it("should detect 'config' for configuration route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.CONFIGURATION_SYSTEM);
      expect(component.activeSection()).toBe("config");
    });

    it("should detect 'token' for tokens route", () => {
      contentService.routeUrl.set(ROUTE_PATHS.TOKENS);
      expect(component.activeSection()).toBe("token");
    });
  });

  describe("dashboard toolbar actions", () => {
    let layoutService: DashboardLayoutService;

    beforeEach(() => {
      layoutService = TestBed.inject(DashboardLayoutService);
      layoutService.editMode.set(false);
    });

    it("should begin a staged edit when entering edit mode", () => {
      const beginSpy = jest.spyOn(layoutService, "beginEdit");
      component.enterDashboardEdit();
      expect(beginSpy).toHaveBeenCalled();
      expect(layoutService.editMode()).toBe(true);
    });

    it("should commit the staged edit on save", () => {
      const saveSpy = jest.spyOn(layoutService, "saveEdit");
      component.enterDashboardEdit();
      component.saveDashboard();
      expect(saveSpy).toHaveBeenCalled();
      expect(layoutService.editMode()).toBe(false);
    });

    it("should discard the staged edit on cancel", () => {
      const cancelSpy = jest.spyOn(layoutService, "cancelEdit");
      component.enterDashboardEdit();
      component.cancelDashboard();
      expect(cancelSpy).toHaveBeenCalled();
      expect(layoutService.editMode()).toBe(false);
    });

    it("should register the pending-changes save hook while editing", () => {
      const pendingChanges = TestBed.inject(PendingChangesService);
      component.enterDashboardEdit();
      expect(pendingChanges.hasSaveFn).toBe(true);

      component.saveDashboard();
      expect(pendingChanges.hasSaveFn).toBe(false);
    });

    it("should detect 'dashboard' for dashboard route", () => {
      const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
      contentService.routeUrl.set(ROUTE_PATHS.DASHBOARD);
      expect(component.activeSection()).toBe("dashboard");
    });
  });
});
