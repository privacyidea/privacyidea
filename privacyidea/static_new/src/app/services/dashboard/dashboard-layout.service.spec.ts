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
import { DashboardLayoutService } from "./dashboard-layout.service";
import { DashboardPersistenceService } from "./dashboard-persistence.service";

describe("DashboardLayoutService", () => {
  let service: DashboardLayoutService;
  let persistence: DashboardPersistenceService;

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
      providers: [provideZonelessChangeDetection()]
    });
  });

  describe("initialisation", () => {
    it("should fall back to the default layout when persistence is empty", () => {
      build();
      expect(service.widgets()).toHaveLength(1);
      expect(service.widgets()[0].type).toBe("welcome");
    });

    it("should load an existing layout from persistence", () => {
      const stored: WidgetInstance[] = [{ id: "stat-1", type: "stat", x: 2, y: 3, cols: 4, rows: 4 }];
      build(stored);

      expect(service.widgets()).toEqual(stored);
    });

    it("should start in view mode", () => {
      build();
      expect(service.editMode()).toBe(false);
    });
  });

  describe("editMode", () => {
    beforeEach(() => build());

    it("should toggle the edit mode flag", () => {
      service.toggleEditMode();
      expect(service.editMode()).toBe(true);
      service.toggleEditMode();
      expect(service.editMode()).toBe(false);
    });
  });

  describe("addWidget", () => {
    beforeEach(() => build());

    it("should add a widget with the definition's default size", () => {
      service.addWidget("stat");

      const added = service.widgets().find((widget) => widget.type === "stat");
      expect(added).toBeDefined();
      expect(added?.cols).toBe(4);
      expect(added?.rows).toBe(4);
    });

    it("should place the new widget so it does not overlap existing ones", () => {
      service.addWidget("stat");
      const [first, second] = service.widgets();
      expect(overlaps(first, second)).toBe(false);
    });

    it("should keep new widgets within the column grid", () => {
      service.addWidget("stat");
      for (const widget of service.widgets()) {
        expect(widget.x).toBeGreaterThanOrEqual(0);
        expect(widget.x + widget.cols).toBeLessThanOrEqual(DASHBOARD_COLUMNS);
      }
    });

    it("should insert at the preferred row when scrolled down", () => {
      service.insertRow.set(10);
      service.addWidget("stat");

      const added = service.widgets().find((widget) => widget.type === "stat");
      expect(added?.y).toBeGreaterThanOrEqual(10);
    });

    it("should ignore unknown widget types", () => {
      const before = service.widgets().length;
      service.addWidget("nope");
      expect(service.widgets()).toHaveLength(before);
    });

    it("should persist the layout after adding", () => {
      service.addWidget("stat");
      expect(persistence.load()).toHaveLength(2);
    });
  });

  describe("removeWidget", () => {
    beforeEach(() => build());

    it("should remove the widget with the given id", () => {
      const id = service.widgets()[0].id;
      service.removeWidget(id);
      expect(service.widgets()).toHaveLength(0);
    });

    it("should leave the layout untouched for an unknown id", () => {
      service.removeWidget("missing");
      expect(service.widgets()).toHaveLength(1);
    });

    it("should persist after removing", () => {
      const id = service.widgets()[0].id;
      service.removeWidget(id);
      expect(persistence.load()).toHaveLength(0);
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
      service.addWidget("stat");
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

    it("should restore the default single-welcome layout", () => {
      service.addWidget("stat");
      service.resetLayout();

      expect(service.widgets()).toHaveLength(1);
      expect(service.widgets()[0].type).toBe("welcome");
    });

    it("should persist the reset layout", () => {
      service.addWidget("stat");
      service.resetLayout();
      expect(persistence.load()).toHaveLength(1);
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
});
