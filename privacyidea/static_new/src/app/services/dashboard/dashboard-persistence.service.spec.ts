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
import { WidgetInstance } from "@models/dashboard";
import { DashboardPersistenceService } from "./dashboard-persistence.service";

describe("DashboardPersistenceService", () => {
  let service: DashboardPersistenceService;

  const sampleWidgets = (): WidgetInstance[] => [{ id: "w1", type: "tokens", x: 0, y: 0, cols: 6, rows: 8 }];

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), DashboardPersistenceService]
    });
    service = TestBed.inject(DashboardPersistenceService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should return null before anything is saved", () => {
    expect(service.load()).toBeNull();
  });

  it("should return the saved widgets", () => {
    const widgets = sampleWidgets();
    service.save(widgets);

    expect(service.load()).toEqual(widgets);
  });

  it("should store a clone so later mutations of the input do not leak in", () => {
    const widgets = sampleWidgets();
    service.save(widgets);

    widgets[0].x = 99;
    widgets.push({ id: "w2", type: "events", x: 0, y: 0, cols: 8, rows: 5 });

    const loaded = service.load();
    expect(loaded).toHaveLength(1);
    expect(loaded?.[0].x).toBe(0);
  });

  it("should return a fresh clone on each load so callers cannot mutate the store", () => {
    service.save(sampleWidgets());

    const first = service.load();
    first![0].x = 42;

    const second = service.load();
    expect(second?.[0].x).toBe(0);
    expect(second).not.toBe(first);
  });

  it("should overwrite previously saved widgets", () => {
    service.save(sampleWidgets());
    service.save([]);

    expect(service.load()).toEqual([]);
  });
});
