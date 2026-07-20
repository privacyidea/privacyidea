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
import { TestBed } from "@angular/core/testing";
import { DASHBOARD_COLUMNS, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { DashboardLayoutService } from "./dashboard-layout.service";
import { DashboardPersistenceService } from "./dashboard-persistence.service";

describe("DashboardLayoutService", () => {
  let service: DashboardLayoutService;
  let persistence: DashboardPersistenceService;
  let auth: MockAuthService;

  const overlaps = (a: WidgetInstance, b: WidgetInstance): boolean =>
    a.x < b.x + b.cols && a.x + a.cols > b.x && a.y < b.y + b.rows && a.y + a.rows > b.y;

  /** Builds the service after optionally seeding persistence, so the constructor picks up the stored layout. */
  const build = (seed?: WidgetInstance[]): void => {
    persistence = TestBed.inject(DashboardPersistenceService);
    if (seed) {
      persistence.save(seed);
    }
    service = TestBed.inject(DashboardLayoutService);
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), { provide: AuthService, useClass: MockAuthService }]
    });
    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    auth.actionAllowed.mockReturnValue(true);
  });

  describe("initialisation", () => {
    it("should fall back to the default layout when persistence is empty", () => {
      build();
      expect(service.widgets()).toHaveLength(7);
      expect(service.widgets().map((widget) => widget.type).sort()).toEqual([
        "administration",
        "authentications",
        "events",
        "policies",
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

    it("should always include the pinned widget at its fixed position", () => {
      build();
      const pinned = service.widgets().find((widget) => widget.type === "subscriptions");
      expect(pinned).toMatchObject({ x: 16, y: 0 });
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
      expect((persistence.load() ?? []).some((widget) => widget.type === "events")).toBe(false);
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
      expect(persistence.load()?.some((widget) => widget.type === "events")).toBe(true);
    });

    it("should revert the staged layout on cancelEdit", () => {
      service.beginEdit();
      service.addWidget("events");
      service.cancelEdit();
      expect(service.editMode()).toBe(false);
      expect(service.widgets().some((widget) => widget.type === "events")).toBe(false);
      expect((persistence.load() ?? []).some((widget) => widget.type === "events")).toBe(false);
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
      expect(persistence.load()).toHaveLength(before + 1);
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
      const pinned = service.widgets().find((widget) => widget.type === "subscriptions")!;
      service.removeWidget(pinned.id);
      expect(service.widgets().some((widget) => widget.type === "subscriptions")).toBe(true);
    });

    it("should leave the layout untouched for an unknown id", () => {
      const before = service.widgets().length;
      service.removeWidget("missing");
      expect(service.widgets()).toHaveLength(before);
    });

    it("should persist after removing", () => {
      const tokens = service.widgets().find((widget) => widget.type === "tokens")!;
      service.removeWidget(tokens.id);
      expect(persistence.load()?.some((widget) => widget.type === "tokens")).toBe(false);
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
      const stored = persistence.load()?.find((widget) => widget.id === id);
      expect(stored).toMatchObject({ x: 3, y: 3 });
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
      const stored = persistence.load()?.find((widget) => widget.id === id);
      expect(stored).toMatchObject({ cols: 12, rows: 5 });
    });
  });

  describe("resetLayout", () => {
    beforeEach(() => build());

    it("should restore the default layout", () => {
      service.removeWidget(service.widgets().find((widget) => widget.type === "events")!.id);
      service.resetLayout();

      expect(service.widgets()).toHaveLength(7);
      expect(service.widgets().map((widget) => widget.type).sort()).toEqual([
        "administration",
        "authentications",
        "events",
        "policies",
        "subscriptions",
        "token-types",
        "tokens"
      ]);
    });

    it("should persist the reset layout", () => {
      service.removeWidget(service.widgets().find((widget) => widget.type === "events")!.id);
      service.resetLayout();
      expect(persistence.load()).toHaveLength(7);
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

    it("should not add a widget the user is not allowed to see", () => {
      build([]);
      auth.actionAllowed.mockImplementation((action: string) => action !== "events_handling_read" && action !== "eventhandling_read");
      service.addWidget("events");
      expect(service.hasWidgetOfType("events")).toBe(false);
    });

    it("should remove forbidden widgets from the layout and persist the pruned state", () => {
      build();
      auth.actionAllowed.mockImplementation((action: string) => action !== "tokenlist");

      service.pruneForbiddenWidgets();

      expect(service.hasWidgetOfType("tokens")).toBe(false);
      expect(persistence.load()?.some((widget) => widget.type === "tokens")).toBe(false);
    });

    it("should keep allowed and pinned widgets when pruning", () => {
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
});
