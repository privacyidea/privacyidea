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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideZonelessChangeDetection } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { DASHBOARD_COLUMNS, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { MockNotificationService } from "@testing/mock-services";
import { DashboardLayoutService } from "./dashboard-layout.service";
import { DashboardPersistenceService } from "./dashboard-persistence.service";
import { Subject } from "rxjs";

describe("DashboardLayoutService", () => {
  let service: DashboardLayoutService;
  let persistence: DashboardPersistenceService;
  let auth: MockAuthService;

  const overlaps = (a: WidgetInstance, b: WidgetInstance): boolean =>
    a.x < b.x + b.cols && a.x + a.cols > b.x && a.y < b.y + b.rows && a.y + a.rows > b.y;

  /** Reads the layout currently persisted in the mocked user settings. */
  const persisted = (): WidgetInstance[] | null => {
    const settings = TestBed.inject(UserSettingsService) as unknown as MockUserSettingsService;
    return (settings.settings()?.["dashboard"] as { widgets?: WidgetInstance[] } | undefined)?.widgets ?? null;
  };

  /** Reads the stored layout back; the mocked user settings resolve synchronously. */
  const stored = (): WidgetInstance[] | null => {
    let result: WidgetInstance[] | null = null;
    persistence.load().subscribe((widgets) => {
      result = widgets;
    });
    return result;
  };

  /** Builds the service after optionally seeding persistence, so the constructor picks up the stored layout. */
  const build = (seed?: WidgetInstance[]): void => {
    persistence = TestBed.inject(DashboardPersistenceService);
    if (seed) {
      persistence.save(seed).subscribe();
    }
    service = TestBed.inject(DashboardLayoutService);
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserSettingsService, useClass: MockUserSettingsService }
      ]
    });
    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    auth.actionAllowed.mockReturnValue(true);
  });

  describe("initialisation", () => {
    it("should fall back to the default layout when persistence is empty", () => {
      build();
      expect(service.widgets()).toHaveLength(10);
      expect(
        service
          .widgets()
          .map((widget) => widget.type)
          .sort()
      ).toEqual([
        "authentication-activity",
        "certificate-health",
        "conditional-access",
        "news",
        "notification-delivery",
        "policies",
        "resolver-timing",
        "subscriptions",
        "token-types",
        "tokens"
      ]);
    });

    it("should load an existing layout from persistence", () => {
      const stored: WidgetInstance[] = [{ id: "events-1", type: "events", x: 2, y: 3, cols: 8, rows: 5 }];
      build(stored);

      expect(service.widgets()).toContainEqual(stored[0]);
    });

    it("should pin news and subscriptions to the right in the default layout", () => {
      build();
      const news = service.widgets().find((widget) => widget.type === "news");
      const subscriptions = service.widgets().find((widget) => widget.type === "subscriptions");
      expect(news).toMatchObject({ x: 16, y: 0, cols: 8, rows: 3 });
      expect(subscriptions).toMatchObject({ x: 16, y: 3, cols: 8, rows: 8 });
    });

    it("should open the default layout with authentication activity in the top left corner", () => {
      build();
      const activity = service.widgets().find((widget) => widget.type === "authentication-activity");
      expect(activity).toMatchObject({ x: 0, y: 0 });
    });

    it("should not overlap any two widgets in the default layout", () => {
      build();
      const widgets = service.widgets();
      for (let i = 0; i < widgets.length; i++) {
        for (let j = i + 1; j < widgets.length; j++) {
          expect(overlaps(widgets[i], widgets[j])).toBe(false);
        }
      }
    });

    it("should leave out a pinned widget the admin may not see", () => {
      auth.actionAllowed.mockImplementation((action: string) => action !== "managesubscription");
      build();
      expect(service.hasWidgetOfType("subscriptions")).toBe(false);
    });

    it("should drop a stored widget that overlaps a pinned one", () => {
      build([
        { id: "tokens-1", type: "tokens", x: 18, y: 1, cols: 6, rows: 4 },
        { id: "policies-1", type: "policies", x: 0, y: 0, cols: 10, rows: 5 }
      ]);
      expect(service.hasWidgetOfType("tokens")).toBe(false);
      expect(service.hasWidgetOfType("policies")).toBe(true);
    });

    it("should keep only the first of two stored widgets that overlap each other", () => {
      build([
        { id: "policies-1", type: "policies", x: 0, y: 0, cols: 10, rows: 5 },
        { id: "tokens-1", type: "tokens", x: 2, y: 2, cols: 6, rows: 4 }
      ]);
      expect(service.hasWidgetOfType("policies")).toBe(true);
      expect(service.hasWidgetOfType("tokens")).toBe(false);
    });

    it("should start in view mode", () => {
      build();
      expect(service.editMode()).toBe(false);
    });
  });

  describe("staged editing", () => {
    beforeEach(() => build([]));

    it("should enter edit mode on beginEdit", () => {
      service.beginEdit();
      expect(service.editMode()).toBe(true);
      expect(service.hasPendingChanges()).toBe(false);
    });

    it("should not persist changes made while editing", () => {
      service.beginEdit();
      const saveSpy = jest.spyOn(persistence, "save");
      service.addWidget("events");
      expect(saveSpy).not.toHaveBeenCalled();
      expect((stored() ?? []).some((widget) => widget.type === "events")).toBe(false);
    });

    it("should report pending changes once the layout diverges", () => {
      service.beginEdit();
      expect(service.hasPendingChanges()).toBe(false);
      service.addWidget("events");
      expect(service.hasPendingChanges()).toBe(true);
    });

    it("should persist the staged layout on saveEdit", () => {
      service.beginEdit();
      service.addWidget("events");
      service.saveEdit();
      expect(service.editMode()).toBe(false);
      expect(service.hasPendingChanges()).toBe(false);
      expect(stored()?.some((widget) => widget.type === "events")).toBe(true);
    });

    it("should revert the staged layout on cancelEdit", () => {
      service.beginEdit();
      service.addWidget("events");
      service.cancelEdit();
      expect(service.editMode()).toBe(false);
      expect(service.widgets().some((widget) => widget.type === "events")).toBe(false);
      expect((stored() ?? []).some((widget) => widget.type === "events")).toBe(false);
    });

    it("should report pending changes for a settings-only change", () => {
      service.addWidget("events");
      const id = service.widgets()[0].id;
      service.beginEdit();
      expect(service.hasPendingChanges()).toBe(false);
      service.updateWidgetSettings(id, { realm: "realm1" });
      expect(service.hasPendingChanges()).toBe(true);
    });

    it("should revert a staged settings change on cancelEdit", () => {
      service.addWidget("events");
      const id = service.widgets()[0].id;
      service.beginEdit();
      service.updateWidgetSettings(id, { realm: "realm1" });
      service.cancelEdit();
      expect(service.widgets().find((widget) => widget.id === id)?.settings).toBeUndefined();
    });
  });

  describe("addWidget", () => {
    beforeEach(() => build([]));

    it("should add a widget with the definition's default size", () => {
      service.addWidget("events");

      const added = service.widgets().find((widget) => widget.type === "events");
      expect(added).toBeDefined();
      expect(added?.cols).toBe(6);
      expect(added?.rows).toBe(3);
    });

    it("should place the new widget so it does not overlap existing ones", () => {
      service.addWidget("events");
      const added = service.widgets().find((widget) => widget.type === "events")!;
      for (const other of service.widgets().filter((widget) => widget.id !== added.id)) {
        expect(overlaps(added, other)).toBe(false);
      }
    });

    it("should keep new widgets within the column grid", () => {
      service.addWidget("events");
      for (const widget of service.widgets()) {
        expect(widget.x).toBeGreaterThanOrEqual(0);
        expect(widget.x + widget.cols).toBeLessThanOrEqual(DASHBOARD_COLUMNS);
      }
    });

    it("should insert at the preferred row when scrolled down", () => {
      service.insertRow.set(10);
      service.addWidget("events");

      const added = service.widgets().find((widget) => widget.type === "events");
      expect(added?.y).toBeGreaterThanOrEqual(10);
    });

    it("should ignore unknown widget types", () => {
      const before = service.widgets().length;
      service.addWidget("nope");
      expect(service.widgets()).toHaveLength(before);
    });

    it("should persist the layout after adding", () => {
      const before = service.widgets().length;
      service.addWidget("events");
      expect(stored()).toHaveLength(before + 1);
    });

    it("should not add a second widget of a type that is already placed", () => {
      service.addWidget("events");
      const countAfterFirst = service.widgets().filter((widget) => widget.type === "events").length;

      service.addWidget("events");
      const countAfterSecond = service.widgets().filter((widget) => widget.type === "events").length;

      expect(countAfterFirst).toBe(1);
      expect(countAfterSecond).toBe(1);
    });
  });

  describe("hasWidgetOfType", () => {
    beforeEach(() => build([]));

    it("should report whether a widget type is present in the layout", () => {
      expect(service.hasWidgetOfType("events")).toBe(false);
      service.addWidget("events");
      expect(service.hasWidgetOfType("events")).toBe(true);
    });
  });

  describe("removeWidget", () => {
    beforeEach(() => build());

    it("should remove a non-pinned widget with the given id", () => {
      const tokens = service.widgets().find((widget) => widget.type === "tokens")!;
      service.removeWidget(tokens.id);
      expect(service.widgets().some((widget) => widget.type === "tokens")).toBe(false);
    });

    it("should not remove a pinned widget", () => {
      const news = service.widgets().find((widget) => widget.type === "news")!;

      service.removeWidget(news.id);

      expect(service.hasWidgetOfType("news")).toBe(true);
    });

    it("should leave the layout untouched for an unknown id", () => {
      const before = service.widgets().length;
      service.removeWidget("missing");
      expect(service.widgets()).toHaveLength(before);
    });

    it("should persist after removing", () => {
      const tokens = service.widgets().find((widget) => widget.type === "tokens")!;
      service.removeWidget(tokens.id);
      expect(stored()?.some((widget) => widget.type === "tokens")).toBe(false);
    });
  });

  describe("moveWidgetTo", () => {
    beforeEach(() => build());

    it("should update the position of the matching widget", () => {
      const id = service.widgets()[0].id;
      service.moveWidgetTo(id, 5, 7);

      const moved = service.widgets()[0];
      expect(moved.x).toBe(5);
      expect(moved.y).toBe(7);
    });

    it("should not change other widgets", () => {
      service.addWidget("events");
      const target = service.widgets()[0];
      const other = service.widgets()[1];
      const otherBefore = { ...other };

      service.moveWidgetTo(target.id, 1, 1);

      expect(service.widgets()[1]).toEqual(otherBefore);
    });

    it("should persist after moving", () => {
      const id = service.widgets()[0].id;
      service.moveWidgetTo(id, 3, 3);
      const storedWidget = stored()?.find((widget) => widget.id === id);
      expect(storedWidget).toMatchObject({ x: 3, y: 3 });
    });
  });

  describe("resizeWidget", () => {
    beforeEach(() => build());

    it("should update the size of the matching widget", () => {
      const id = service.widgets()[0].id;
      service.resizeWidget(id, 10, 6);

      const resized = service.widgets()[0];
      expect(resized.cols).toBe(10);
      expect(resized.rows).toBe(6);
    });

    it("should persist after resizing", () => {
      const id = service.widgets()[0].id;
      service.resizeWidget(id, 12, 5);
      const storedWidget = stored()?.find((widget) => widget.id === id);
      expect(storedWidget).toMatchObject({ cols: 12, rows: 5 });
    });
  });

  describe("updateWidgetSettings", () => {
    beforeEach(() => build());

    it("should attach the settings to the matching widget", () => {
      const id = service.widgets()[0].id;
      service.updateWidgetSettings(id, { realm: "realm1" });

      expect(service.widgets()[0].settings).toEqual({ realm: "realm1" });
    });

    it("should merge into, not replace, previously stored settings", () => {
      const id = service.widgets()[0].id;
      service.updateWidgetSettings(id, { realm: "realm1", extra: "kept" });
      service.updateWidgetSettings(id, { realm: "realm2" });

      expect(service.widgets()[0].settings).toEqual({ realm: "realm2", extra: "kept" });
    });

    it("should not change other widgets", () => {
      service.addWidget("events");
      const target = service.widgets()[0];
      const other = service.widgets()[1];
      const otherBefore = { ...other };

      service.updateWidgetSettings(target.id, { realm: "realm1" });

      expect(service.widgets()[1]).toEqual(otherBefore);
    });

    it("should do nothing for an id that does not match any widget", () => {
      const before = service.widgets();
      service.updateWidgetSettings("does-not-exist", { realm: "realm1" });

      expect(service.widgets()).toEqual(before);
    });

    it("should persist after updating settings", () => {
      const id = service.widgets()[0].id;
      service.updateWidgetSettings(id, { realm: "realm1" });

      const storedWidget = stored()?.find((widget) => widget.id === id);
      expect(storedWidget?.settings).toEqual({ realm: "realm1" });
    });
  });

  describe("setWidgetOptions", () => {
    beforeEach(() => build());

    it("should merge into the options the widget already has", () => {
      const id = service.widgets()[0].id;
      service.setWidgetOptions(id, { range: "24h" });
      service.setWidgetOptions(id, {});

      expect(service.widgets()[0].options).toEqual({ range: "24h" });
    });

    it("should persist the options", () => {
      const id = service.widgets()[0].id;
      service.setWidgetOptions(id, { range: "6h" });

      expect(stored()?.find((widget) => widget.id === id)?.options).toEqual({ range: "6h" });
    });

    it("should leave every other widget alone", () => {
      const [first, second] = service.widgets();
      service.setWidgetOptions(first.id, { range: "24h" });

      expect(service.widgets().find((widget) => widget.id === second.id)?.options).toBeUndefined();
    });

    it("should survive a cancelled arrangement, the window being a way of reading the widget and not a layout", () => {
      const { id, x, y } = service.widgets()[0];
      service.beginEdit();
      service.setWidgetOptions(id, { range: "24h" });
      service.moveWidgetTo(id, x + 2, y + 2);
      service.cancelEdit();

      const widget = service.widgets().find((candidate) => candidate.id === id);
      expect(widget?.options).toEqual({ range: "24h" });
      expect(widget).toMatchObject({ x, y });
    });
  });

  describe("resetLayout", () => {
    beforeEach(() => build());

    it("should restore the default layout", () => {
      service.removeWidget(service.widgets().find((widget) => widget.type === "tokens")!.id);
      service.resetLayout();

      expect(service.widgets()).toHaveLength(10);
      expect(
        service
          .widgets()
          .map((widget) => widget.type)
          .sort()
      ).toEqual([
        "authentication-activity",
        "certificate-health",
        "conditional-access",
        "news",
        "notification-delivery",
        "policies",
        "resolver-timing",
        "subscriptions",
        "token-types",
        "tokens"
      ]);
    });

    it("should persist the reset layout", () => {
      service.removeWidget(service.widgets().find((widget) => widget.type === "tokens")!.id);
      service.resetLayout();
      expect(stored()).toHaveLength(10);
    });

    it("should keep the id and options of a widget that was already on the dashboard", () => {
      const tokens = service.widgets().find((widget) => widget.type === "tokens")!;
      service.moveWidgetTo(tokens.id, 0, 30);
      service.setWidgetOptions(tokens.id, { range: "7d" });

      service.resetLayout();

      expect(service.widgets().find((widget) => widget.type === "tokens")).toMatchObject({
        id: tokens.id,
        x: 6,
        y: 0,
        options: { range: "7d" }
      });
    });

    it("should leave out widgets the admin may not see", () => {
      auth.actionAllowed.mockImplementation((action: string) => action !== "authentication_log_read");
      service.resetLayout();
      expect(service.hasWidgetOfType("authentication-activity")).toBe(false);
    });

    it("should move widgets up into the gap a forbidden widget leaves", () => {
      auth.actionAllowed.mockImplementation((action: string) => action !== "managesubscription");
      service.resetLayout();
      expect(service.widgets().find((widget) => widget.type === "notification-delivery")).toMatchObject({
        x: 16,
        y: 3
      });
    });

    it("should not move a widget up past another one", () => {
      auth.actionAllowed.mockImplementation((action: string) => action !== "authentication_log_read");
      service.resetLayout();
      expect(service.widgets().find((widget) => widget.type === "resolver-timing")).toMatchObject({ x: 0, y: 8 });
    });
  });

  describe("persist", () => {
    beforeEach(() => build());

    it("should write the current layout to persistence", () => {
      const saveSpy = jest.spyOn(persistence, "save");
      service.persist();
      expect(saveSpy).toHaveBeenCalledWith(service.widgets());
    });
  });

  describe("permission filtering", () => {
    it("should report a widget type as allowed when its required action is granted", () => {
      build([]);
      expect(service.isWidgetTypeAllowed("tokens")).toBe(true);
    });

    it("should report a widget type as forbidden when its required action is missing", () => {
      build([]);
      auth.actionAllowed.mockImplementation((action: string) => action !== "tokenlist");
      expect(service.isWidgetTypeAllowed("tokens")).toBe(false);
    });

    it("should report a widget type that names no required action as allowed", () => {
      build([]);
      auth.actionAllowed.mockReturnValue(false);
      expect(service.isWidgetTypeAllowed("certificate-health")).toBe(true);
    });

    it("should report a widget type with several required actions as allowed on any one of them", () => {
      build([]);
      auth.actionAllowed.mockImplementation((action: string) => action === "blocklist_read");
      expect(service.isWidgetTypeAllowed("conditional-access")).toBe(true);
    });

    it("should report a widget type with several required actions as forbidden when none is granted", () => {
      build([]);
      auth.actionAllowed.mockImplementation(
        (action: string) => !["conditional_access_policy_read", "user_lock_read", "blocklist_read"].includes(action)
      );
      expect(service.isWidgetTypeAllowed("conditional-access")).toBe(false);
    });

    it("should not add a widget the user is not allowed to see", () => {
      build([]);
      auth.actionAllowed.mockImplementation(
        (action: string) => action !== "events_handling_read" && action !== "eventhandling_read"
      );
      service.addWidget("events");
      expect(service.hasWidgetOfType("events")).toBe(false);
    });

    it("should remove forbidden widgets from the layout and persist the pruned state", () => {
      build();
      auth.actionAllowed.mockImplementation((action: string) => action !== "tokenlist");

      service.pruneForbiddenWidgets();

      expect(service.hasWidgetOfType("tokens")).toBe(false);
      expect(stored()?.some((widget) => widget.type === "tokens")).toBe(false);
    });

    it("should keep the allowed widgets when pruning", () => {
      build();
      auth.actionAllowed.mockImplementation((action: string) => action !== "tokenlist");

      service.pruneForbiddenWidgets();

      expect(service.hasWidgetOfType("policies")).toBe(true);
      expect(service.hasWidgetOfType("subscriptions")).toBe(true);
    });

    it("should not touch the layout when auth data is not yet available", () => {
      build();
      auth.isAuthenticated.set(false);
      auth.actionAllowed.mockReturnValue(false);
      const before = service.widgets().length;

      service.pruneForbiddenWidgets();

      expect(service.widgets()).toHaveLength(before);
    });
  });

  describe("session boundaries", () => {
    /** A load whose response is held back until the test releases it. */
    const buildWithDeferredLoad = (): { deferred: Subject<WidgetInstance[] | null> } => {
      const deferred = new Subject<WidgetInstance[] | null>();
      persistence = TestBed.inject(DashboardPersistenceService);
      jest.spyOn(persistence, "load").mockReturnValue(deferred.asObservable());
      service = TestBed.inject(DashboardLayoutService);
      return { deferred };
    };

    it("drops an in-progress edit of the ended session along with its layout", () => {
      build();
      service.beginEdit();
      expect(service.editMode()).toBe(true);

      auth.isAuthenticated.set(false);
      TestBed.flushEffects();

      expect(service.editMode()).toBe(false);
    });

    it("does not carry the previous session's layout into the next one", () => {
      const first: WidgetInstance[] = [{ id: "events-a", type: "events", x: 0, y: 0, cols: 8, rows: 5 }];
      build(first);
      expect(service.widgets()).toContainEqual(first[0]);

      // Logout: the auth service ends the session, the layout service reacts to it.
      auth.isAuthenticated.set(false);
      TestBed.flushEffects();
      expect(service.widgets()).not.toContainEqual(first[0]);

      // Another administrator signs in without the page reloading; their stored layout differs.
      const second: WidgetInstance[] = [{ id: "policies-b", type: "policies", x: 0, y: 0, cols: 10, rows: 5 }];
      persistence.save(second).subscribe();
      auth.isAuthenticated.set(true);
      service.ensureLoadedForSession();

      expect(service.widgets()).toContainEqual(second[0]);
      expect(service.widgets()).not.toContainEqual(first[0]);
    });

    it("drops a load that a logout superseded", () => {
      const { deferred } = buildWithDeferredLoad();

      // The session ends while its load is still in flight.
      auth.isAuthenticated.set(false);
      TestBed.flushEffects();

      // The response of the session that just ended arrives late: it must not apply.
      deferred.next([{ id: "events-a", type: "events", x: 0, y: 0, cols: 8, rows: 5 }]);
      deferred.complete();

      expect(service.hasWidgetOfType("events")).toBe(false);
      // The plain defaults, not reconciled: with the session gone there is no role to
      // reconcile against, so the pinned widgets are absent as well.
      expect(service.hasWidgetOfType("subscriptions")).toBe(false);

      // The next session loads its own stored layout.
      jest.restoreAllMocks();
      const second: WidgetInstance[] = [{ id: "policies-b", type: "policies", x: 0, y: 0, cols: 10, rows: 5 }];
      persistence.save(second).subscribe();
      auth.isAuthenticated.set(true);
      service.ensureLoadedForSession();

      expect(service.widgets()).toContainEqual(second[0]);
      expect(service.hasWidgetOfType("events")).toBe(false);
    });

    it("prunes the stored layout only after it has loaded, so pruned defaults are never saved over it", () => {
      const { deferred } = buildWithDeferredLoad();
      // The admin may not see the tokens widgets (tokenlist) but may see policies.
      auth.actionAllowed.mockImplementation((action: string) => action !== "tokenlist");

      // The dashboard mounts while the stored layout is still in flight and prunes.
      service.pruneForbiddenWidgets();

      // The stored layout arrives: one forbidden widget, one allowed.
      deferred.next([
        { id: "tokens-b", type: "tokens", x: 0, y: 0, cols: 6, rows: 4 },
        { id: "policies-b", type: "policies", x: 6, y: 0, cols: 10, rows: 5 }
      ]);
      deferred.complete();

      expect(service.hasWidgetOfType("tokens")).toBe(false);
      expect(service.hasWidgetOfType("policies")).toBe(true);
      // What is persisted is the stored layout minus the forbidden widget, not the defaults.
      expect(persisted()?.some((widget) => widget.id === "policies-b")).toBe(true);
      expect(persisted()?.some((widget) => widget.id === "tokens-b")).toBe(false);
      expect(persisted()?.some((widget) => widget.type === "resolver-timing")).toBe(false);
    });

    it("keeps a layout the user changed while the load was in flight", () => {
      const { deferred } = buildWithDeferredLoad();

      // The user adds a widget before their stored layout arrives.
      service.addWidget("events");
      expect(service.hasWidgetOfType("events")).toBe(true);

      deferred.next([{ id: "policies-a", type: "policies", x: 0, y: 0, cols: 10, rows: 5 }]);
      deferred.complete();

      // The in-flight change wins and is written back, and the stored layout does not apply.
      expect(service.hasWidgetOfType("events")).toBe(true);
      expect(service.widgets().some((widget) => widget.id === "policies-a")).toBe(false);
      expect(persisted()?.some((widget) => widget.type === "events")).toBe(true);
    });

    it("does not start a second load while one is in flight, or after the layout settled", () => {
      const { deferred } = buildWithDeferredLoad();
      const loadSpy = persistence.load as jest.Mock;

      service.ensureLoadedForSession();
      expect(loadSpy).toHaveBeenCalledTimes(1);

      deferred.next(null);
      deferred.complete();
      expect(loadSpy).toHaveBeenCalledTimes(1);

      service.ensureLoadedForSession();
      expect(loadSpy).toHaveBeenCalledTimes(1);
    });

    it("hides forbidden default widgets while the stored layout is on its way", () => {
      const { deferred } = buildWithDeferredLoad();
      // The admin may not see the tokens widgets, but may see policies.
      auth.actionAllowed.mockImplementation((action: string) => action !== "tokenlist");

      // The dashboard mounts before the stored layout arrives and prunes.
      service.pruneForbiddenWidgets();

      // The displayed defaults are filtered for the wait...
      expect(service.hasWidgetOfType("tokens")).toBe(false);
      expect(service.hasWidgetOfType("policies")).toBe(true);
      // ...without anything being written over the stored layout that has not arrived yet.
      expect(persisted()).toBeNull();

      // The stored layout arrives; the pending prune acts on it, and what is
      // persisted is the stored layout minus the forbidden widget, not the defaults.
      deferred.next([
        { id: "tokens-b", type: "tokens", x: 0, y: 0, cols: 6, rows: 4 },
        { id: "policies-b", type: "policies", x: 6, y: 0, cols: 10, rows: 5 }
      ]);
      deferred.complete();

      expect(service.hasWidgetOfType("tokens")).toBe(false);
      expect(service.hasWidgetOfType("policies")).toBe(true);
      expect(persisted()?.some((widget) => widget.id === "tokens-b")).toBe(false);
      expect(persisted()?.some((widget) => widget.id === "policies-b")).toBe(true);
    });

    it("keeps the in-flight marker when a superseded response arrives late", () => {
      const loads: Subject<WidgetInstance[] | null>[] = [];
      persistence = TestBed.inject(DashboardPersistenceService);
      jest.spyOn(persistence, "load").mockImplementation(() => {
        const subject = new Subject<WidgetInstance[] | null>();
        loads.push(subject);
        return subject.asObservable();
      });
      service = TestBed.inject(DashboardLayoutService);
      expect(loads).toHaveLength(1);

      // The session ends while its load is in flight; the next one starts its own.
      auth.isAuthenticated.set(false);
      TestBed.flushEffects();
      auth.isAuthenticated.set(true);
      service.ensureLoadedForSession();
      expect(loads).toHaveLength(2);

      // The superseded response arrives late: it must not apply...
      loads[0].next([{ id: "events-a", type: "events", x: 0, y: 0, cols: 8, rows: 5 }]);
      loads[0].complete();
      expect(service.hasWidgetOfType("events")).toBe(false);

      // ...and it must not clear the in-flight marker of the load that follows:
      // opening an edit while that load is still pending starts no third request.
      service.beginEdit();
      service.cancelEdit();
      expect(loads).toHaveLength(2);

      // The load that is still current settles and applies.
      loads[1].next([{ id: "policies-b", type: "policies", x: 0, y: 0, cols: 10, rows: 5 }]);
      loads[1].complete();
      expect(service.hasWidgetOfType("policies")).toBe(true);
    });
  });
});

describe("DashboardLayoutService over the real user settings service", () => {
  // The session-boundary tests above mock persistence.load; this one runs the real
  // pipeline, because the cache of the user settings service outlives a logout and
  // can hand the layout of the ended session to the administrator who follows.
  let service: DashboardLayoutService;
  let auth: MockAuthService;
  let httpMock: HttpTestingController;
  let userSettings: UserSettingsService;

  const respondWith = (widgets: WidgetInstance[]): void => {
    const request = httpMock.expectOne("/user/settings");
    request.flush({ result: { status: true, value: { dashboard: { widgets } } } });
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        UserSettingsService,
        DashboardPersistenceService
      ]
    });
    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    auth.actionAllowed.mockReturnValue(true);
    httpMock = TestBed.inject(HttpTestingController);
    userSettings = TestBed.inject(UserSettingsService);
    service = TestBed.inject(DashboardLayoutService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("does not serve the dashboard of an ended session to the next one", () => {
    // Administrator A opens the dashboard; their settings request is on its way.
    const requestA = httpMock.expectOne("/user/settings");

    // A logs out: the session ends and the auth service drops the settings cache.
    auth.isAuthenticated.set(false);
    TestBed.flushEffects();
    userSettings.clearCache();

    // A's response lands after the logout: it must not fill the cleared cache.
    requestA.flush({
      result: {
        status: true,
        value: { dashboard: { widgets: [{ id: "events-a", type: "events", x: 0, y: 0, cols: 8, rows: 5 }] } }
      }
    });
    expect(userSettings.settings()).toBeNull();

    // B signs in without the page reloading and opens the dashboard: a fresh
    // request is sent, and their own stored layout applies.
    auth.isAuthenticated.set(true);
    service.ensureLoadedForSession();
    respondWith([{ id: "policies-b", type: "policies", x: 0, y: 0, cols: 10, rows: 5 }]);

    expect(service.widgets().some((widget) => widget.id === "policies-b")).toBe(true);
    expect(service.widgets().some((widget) => widget.id === "events-a")).toBe(false);
  });
});
