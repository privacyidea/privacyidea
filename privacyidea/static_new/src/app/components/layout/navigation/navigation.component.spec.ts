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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NavigationComponent } from "./navigation.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute, provideRouter, Router } from "@angular/router";
import { provideLocationMocks } from "@angular/common/testing";
import { ROUTE_PATHS } from "../../../route_paths";
import { of } from "rxjs";
import { TokenService } from "../../../services/token/token.service";
import { ContainerService } from "../../../services/container/container.service";
import { ChallengesService } from "../../../services/token/challenges/challenges.service";
import { MachineService } from "../../../services/machine/machine.service";
import { UserService } from "../../../services/user/user.service";
import { AuditService } from "../../../services/audit/audit.service";
import { ContentService } from "../../../services/content/content.service";
import { AuthService } from "../../../services/auth/auth.service";
import { SessionTimerService } from "../../../services/session-timer/session-timer.service";
import { NotificationService } from "../../../services/notification/notification.service";
import {
  MockAuditService,
  MockChallengesService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockMachineService,
  MockNotificationService,
  MockSessionTimerService,
  MockTokenService,
  MockUserService
} from "../../../../testing/mock-services";
import { MatSnackBar } from "@angular/material/snack-bar";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

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
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
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

    // Set active section to "audit" (index 5 in primaryNavItems)
    contentService.routeUrl.set(ROUTE_PATHS.AUDIT);

    // Set visible count to 3
    component.visibleNavCount.set(3);

    const visible = component.visibleNavItems;
    const overflow = component.overflowNavItems;

    // Total filtered items = 8 (assuming all are allowed in MockAuthService)
    // Audit is at index 5. 5 >= 3 is true.
    // Visible should be [items[0], items[1], items[5]]
    expect(visible.length).toBe(3);
    expect(visible[2].section).toBe("audit");

    // Overflow should contain items that were displaced or were already there
    // Indices: 2, 3, 4, 6, 7 (users, policies, events, external, config)
    expect(overflow.length).toBe(5);
    expect(overflow.some(item => item.section === "audit")).toBe(false);
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

    navEl.appendChild(item1);
    navEl.appendChild(item2);

    jest.spyOn(component as any, "getFilteredNavItems").mockReturnValue([
      { section: "token" },
      { section: "container" }
    ]);

    (component as any).calculateVisibleItems(navEl);

    expect(component.visibleNavCount()).toBe(2);

    // Shrink navWidth - should trigger overflow earlier because items are wider than just buttons
    Object.defineProperty(navEl, "clientWidth", { value: 150, configurable: true });
    (component as any).calculateVisibleItems(navEl);
    // item1(100) + gap(4) = 104. 104 > (150 - 80) = 70.
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

    jest.spyOn(component as any, "getFilteredNavItems").mockReturnValue([
      { section: "token" },
      { section: "container" }
    ]);

    // Initial calculation to store widths
    (component as any).calculateVisibleItems(navEl);
    expect(component.visibleNavCount()).toBe(2);

    // Remove item2 from DOM (simulating Angular removing it from visible items)
    navEl.removeChild(item2);

    // Grow container
    Object.defineProperty(navEl, "clientWidth", { value: 500, configurable: true });
    (component as any).calculateVisibleItems(navEl);

    // Should still calculate 2 visible items because it remembers the width of 'container'
    expect(component.visibleNavCount()).toBe(2);
  });
});
