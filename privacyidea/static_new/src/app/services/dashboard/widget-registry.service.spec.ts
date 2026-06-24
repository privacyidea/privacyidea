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
import { DashboardWidget } from "@models/dashboard";
import { WidgetRegistryService } from "./widget-registry.service";

describe("WidgetRegistryService", () => {
  let service: WidgetRegistryService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), WidgetRegistryService]
    });
    service = TestBed.inject(WidgetRegistryService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should expose the built-in widget types", () => {
    const types = service.widgetTypes.map((widget) => widget.type);
    expect(types).toEqual(expect.arrayContaining(["tokens", "subscriptions"]));
  });

  it("should give every widget type a title, icon and positive default size", () => {
    for (const widget of service.widgetTypes) {
      expect(widget.title).toBeTruthy();
      expect(widget.icon).toBeTruthy();
      expect(widget.defaultSize.cols).toBeGreaterThan(0);
      expect(widget.defaultSize.rows).toBeGreaterThan(0);
    }
  });

  it("should never declare a minSize below the global absolute minimum", () => {
    for (const widget of service.widgetTypes) {
      expect(widget.minSize.cols).toBeGreaterThanOrEqual(DashboardWidget.minSize.cols);
      expect(widget.minSize.rows).toBeGreaterThanOrEqual(DashboardWidget.minSize.rows);
    }
  });

  it("should return the widget class for a known type", () => {
    expect(service.get("tokens")?.type).toBe("tokens");
    expect(service.get("subscriptions")?.type).toBe("subscriptions");
  });

  it("should return undefined for an unknown type", () => {
    expect(service.get("does-not-exist")).toBeUndefined();
  });
});
