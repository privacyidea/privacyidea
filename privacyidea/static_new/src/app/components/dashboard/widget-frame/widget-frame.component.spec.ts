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
import { Component, provideZonelessChangeDetection, TemplateRef, viewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { TokensWidgetComponent } from "@components/dashboard/widgets/tokens-widget/tokens-widget.component";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService } from "@services/dashboard/widget-registry.service";
import { InfoService } from "@services/info/info.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { SubscriptionService } from "@services/subscription/subscription.service";
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { MockAuthService, MockInfoService } from "@testing/mock-services";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { WidgetFrameComponent } from "./widget-frame.component";

// No shipped widget is pinned, so the tests for the pinned behaviour stand one in. It
// takes over an existing type id in the registry, which keeps it renderable like any
// other widget while reporting the pinned metadata.
const PINNED_TYPE = "events";

@Component({ selector: "app-pinned-stub-widget", standalone: true, template: "" })
class PinnedStubWidget extends DashboardWidget {
  static override readonly type = PINNED_TYPE;
  static override readonly pinned = true;

  override reload(): void {
    // The stub only carries the pinned metadata; there is nothing to load.
  }
}

// A widget that contributes a button to the frame's header. Stands in for the shipped
// widgets that do, and takes over a type id in the registry the same way.
const ACTIONS_TYPE = "policies";

@Component({
  selector: "app-actions-stub-widget",
  standalone: true,
  template: `<ng-template #headerActions><button class="stub-header-action">act</button></ng-template>`
})
class HeaderActionsStubWidget extends DashboardWidget {
  static override readonly type = ACTIONS_TYPE;
  override readonly headerActions = viewChild<TemplateRef<unknown>>("headerActions");

  constructor() {
    super();
    // Ready rather than loading, so the frame offers its reload button and the order of
    // the two sets of controls can be told apart.
    this.state.set("ready");
  }

  override reload(): void {
    // Nothing to load; the stub exists for the header template.
  }
}

describe("WidgetFrameComponent", () => {
  let fixture: ComponentFixture<WidgetFrameComponent>;
  let component: WidgetFrameComponent;
  let layoutService: DashboardLayoutService;

  const tokensInstance: WidgetInstance = { id: "w1", type: "tokens", x: 0, y: 0, cols: 6, rows: 8 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetFrameComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SubscriptionService, useClass: MockSubscriptionService },
        { provide: InfoService, useClass: MockInfoService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
    }).compileComponents();

    layoutService = TestBed.inject(DashboardLayoutService);
    layoutService.editMode.set(false);

    fixture = TestBed.createComponent(WidgetFrameComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", tokensInstance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should resolve the widget type for the instance type", () => {
    expect(component["widgetType"]()?.type).toBe("tokens");
  });

  it("should resolve the component to render", () => {
    expect(component["component"]()).toBe(TokensWidgetComponent);
  });

  it("should pass the instance through to the outlet inputs", () => {
    expect(component["outletInputs"]()).toEqual({ instance: tokensInstance });
  });

  it("should render the widget title", () => {
    expect(fixture.nativeElement.querySelector(".widget-title").textContent).toContain("Token Usage");
  });

  describe("title link", () => {
    const resolverTimingInstance: WidgetInstance = { id: "r1", type: "resolver-timing", x: 0, y: 0, cols: 12, rows: 6 };

    /**
     * The mock denies every right by default. Rights have to be granted before the frame renders:
     * the real `actionAllowed` reads a signal, so the link recomputes when auth data arrives, but
     * the jest mock has no signal to invalidate the computed with.
     */
    const renderWith = (instance: WidgetInstance, rights: string[]) => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.actionAllowed.mockImplementation((action: string) => rights.includes(action));

      fixture = TestBed.createComponent(WidgetFrameComponent);
      component = fixture.componentInstance;
      fixture.componentRef.setInput("instance", instance);
      fixture.detectChanges();
    };

    const titleLink = () => fixture.nativeElement.querySelector("a.widget-title-link");

    it("should link the title to the matching menu in view mode", () => {
      renderWith(tokensInstance, ["tokenlist"]);

      expect(titleLink()).not.toBeNull();
      expect(titleLink().getAttribute("href")).toBe("/tokens");
    });

    it("should render a plain title in edit mode so the header stays a drag handle", () => {
      renderWith(tokensInstance, ["tokenlist"]);
      layoutService.editMode.set(true);
      fixture.detectChanges();

      expect(titleLink()).toBeNull();
      expect(fixture.nativeElement.querySelector(".widget-title").textContent).toContain("Token Usage");
    });

    it("should not link the title for widgets without a matching menu", () => {
      renderWith({ id: "n1", type: "notification-delivery", x: 0, y: 0, cols: 8, rows: 6 }, ["tokenlist", "auditlog"]);

      expect(titleLink()).toBeNull();
    });

    it("should drop the title link when the user lacks the right for the target page", () => {
      renderWith(resolverTimingInstance, []);

      expect(titleLink()).toBeNull();
    });

    it("should link the resolver timing title once the user may read resolvers", () => {
      renderWith(resolverTimingInstance, ["resolverread"]);

      expect(titleLink().getAttribute("href")).toBe("/users/resolvers");
    });

    // A widget stays on screen without its requiredAction and renders as "denied" instead of being
    // dropped, so the title must not remain a link into a page the user cannot use.
    it("should render a plain title for a denied widget", () => {
      renderWith(tokensInstance, []);

      const widget = component["outlet"]()?.componentInstance as TokensWidgetComponent;
      expect(widget.state()).toBe("denied");
      expect(titleLink()).toBeNull();
      expect(fixture.nativeElement.querySelector(".widget-title").textContent).toContain("Token Usage");
    });

    // Without a right of its own a title link would fall back to "always visible", since the frame
    // cannot infer the target page's right from the widget.
    it("should declare a right for every widget that links its heading", () => {
      const registry = TestBed.inject(WidgetRegistryService);
      const linking = registry.widgetTypes.filter((widgetType) => widgetType.titleLink);

      expect(linking.length).toBeGreaterThan(0);
      expect(linking.filter((widgetType) => !widgetType.titleLinkAction).map((widgetType) => widgetType.type)).toEqual(
        []
      );
    });
  });

  it("should show a reload button when the widget is not loading", () => {
    expect(fixture.nativeElement.querySelector(".widget-reload")).not.toBeNull();
    expect(fixture.nativeElement.querySelector(".widget-loading")).toBeNull();
  });

  it("should hide reload and header spinner while initial loading is active", () => {
    const widget = component["outlet"]()?.componentInstance as TokensWidgetComponent;
    widget.state.set("loading");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".widget-loading")).toBeNull();
    expect(fixture.nativeElement.querySelector(".widget-reload")).toBeNull();
  });

  it("should reload the rendered widget when the reload button is clicked", () => {
    const widget = component["outlet"]()?.componentInstance as TokensWidgetComponent;
    const reloadSpy = jest.spyOn(widget, "reload");

    fixture.nativeElement.querySelector(".widget-reload").click();

    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should hide the remove button in view mode", () => {
    expect(fixture.nativeElement.querySelector(".widget-remove")).toBeNull();
  });

  it("should show the remove button in edit mode", () => {
    layoutService.editMode.set(true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".widget-remove")).not.toBeNull();
  });

  it("should remove the widget from the layout when remove is triggered", () => {
    const removeSpy = jest.spyOn(layoutService, "removeWidget");
    component["remove"]();
    expect(removeSpy).toHaveBeenCalledWith("w1");
  });

  it("should remove the widget when the remove button is clicked in edit mode", () => {
    const removeSpy = jest.spyOn(layoutService, "removeWidget");
    layoutService.editMode.set(true);
    fixture.detectChanges();

    fixture.nativeElement.querySelector(".widget-remove").click();

    expect(removeSpy).toHaveBeenCalledWith("w1");
  });

  describe("widget with a title route", () => {
    const newsInstance: WidgetInstance = { id: "n1", type: "news", x: 0, y: 0, cols: 9, rows: 3 };

    beforeEach(() => {
      const authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
      authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rss_age: 30 });

      fixture = TestBed.createComponent(WidgetFrameComponent);
      component = fixture.componentInstance;
      fixture.componentRef.setInput("instance", newsInstance);
      fixture.detectChanges();
    });

    it("should expose the title route of the widget instance in view mode", () => {
      expect(component["titleLink"]()).toBe(ROUTE_PATHS.NEWS);
    });

    it("should render the title as a link to that route", () => {
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector("a.widget-title");
      expect(link).not.toBeNull();
      expect(link.getAttribute("href")).toBe(ROUTE_PATHS.NEWS);
      expect(link.textContent).toContain("News");
    });

    it("should not link the title in edit mode", () => {
      layoutService.editMode.set(true);
      fixture.detectChanges();

      expect(component["titleLink"]()).toBeNull();
      expect(fixture.nativeElement.querySelector("a.widget-title")).toBeNull();
      expect(fixture.nativeElement.querySelector("span.widget-title").textContent).toContain("News");
    });
  });

  describe("pinned widget", () => {
    const pinnedInstance: WidgetInstance = { id: "p1", type: PINNED_TYPE, x: 16, y: 0, cols: 8, rows: 5 };

    beforeEach(() => {
      const registry = TestBed.inject(WidgetRegistryService);
      const realGet = registry.get.bind(registry);
      jest
        .spyOn(registry, "get")
        .mockImplementation((type: string) => (type === PINNED_TYPE ? PinnedStubWidget : realGet(type)));
      fixture.componentRef.setInput("instance", pinnedInstance);
      layoutService.editMode.set(true);
      fixture.detectChanges();
    });

    it("should report the widget type as pinned", () => {
      expect(component["pinned"]()).toBe(true);
    });

    it("should not offer a remove button in edit mode", () => {
      expect(fixture.nativeElement.querySelector(".widget-remove")).toBeNull();
    });

    it("should not mark the header as draggable in edit mode", () => {
      expect(fixture.nativeElement.querySelector(".widget-header.draggable")).toBeNull();
    });
  });

  describe("widget contributed header actions", () => {
    const actionsInstance: WidgetInstance = { id: "a1", type: ACTIONS_TYPE, x: 0, y: 0, cols: 6, rows: 5 };

    // A frame is created per widget id and never hosts a different widget, so each case
    // gets its own frame rather than swapping the instance on the shared one.
    const frameFor = (instance: WidgetInstance): ComponentFixture<WidgetFrameComponent> => {
      const registry = TestBed.inject(WidgetRegistryService);
      const realGet = registry.get.bind(registry);
      jest
        .spyOn(registry, "get")
        .mockImplementation((type: string) => (type === ACTIONS_TYPE ? HeaderActionsStubWidget : realGet(type)));
      const frame = TestBed.createComponent(WidgetFrameComponent);
      frame.componentRef.setInput("instance", instance);
      frame.detectChanges();
      return frame;
    };

    it("should render them in the header, ahead of the frame's own controls", () => {
      const frame = frameFor(actionsInstance);
      const actions = frame.nativeElement.querySelector(".widget-actions");
      const contributed = actions.querySelector(".stub-header-action");
      const reload = actions.querySelector(".widget-reload");

      expect(contributed).not.toBeNull();
      expect(reload).not.toBeNull();
      // The frame's own controls keep their place, so the reload button does not move from
      // one widget to the next.
      expect(contributed.compareDocumentPosition(reload) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      frame.destroy();
    });

    it("should leave the header alone for a widget that contributes none", () => {
      const frame = frameFor(tokensInstance);

      expect(frame.componentInstance["headerActions"]()).toBeNull();
      expect(frame.nativeElement.querySelector(".stub-header-action")).toBeNull();
      frame.destroy();
    });
  });
});
