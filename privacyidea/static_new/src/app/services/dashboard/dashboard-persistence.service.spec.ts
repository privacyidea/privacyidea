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
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { throwError } from "rxjs";
import { DashboardPersistenceService } from "./dashboard-persistence.service";

describe("DashboardPersistenceService", () => {
  let service: DashboardPersistenceService;
  let userSettings: MockUserSettingsService;

  const sampleWidgets = (): WidgetInstance[] => [{ id: "w1", type: "tokens", x: 0, y: 0, cols: 6, rows: 8 }];

  const loadedWidgets = (): WidgetInstance[] | null => {
    let result: WidgetInstance[] | null = null;
    service.load().subscribe((widgets) => (result = widgets));
    return result;
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: UserSettingsService, useClass: MockUserSettingsService },
        DashboardPersistenceService
      ]
    });
    userSettings = TestBed.inject(UserSettingsService) as unknown as MockUserSettingsService;
    service = TestBed.inject(DashboardPersistenceService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should return null when no dashboard setting is stored", () => {
    expect(loadedWidgets()).toBeNull();
  });

  it("should store the widgets under the dashboard setting key", () => {
    const widgets = sampleWidgets();
    service.save(widgets).subscribe();

    expect(userSettings.settings()?.["dashboard"]).toEqual({ widgets });
  });

  it("should return the saved widgets", () => {
    const widgets = sampleWidgets();
    service.save(widgets).subscribe();

    expect(loadedWidgets()).toEqual(widgets);
  });

  it("should ignore a stored setting that is not a widget list", () => {
    userSettings.settings.set({ dashboard: { widgets: "nonsense" } });

    expect(loadedWidgets()).toBeNull();
  });

  it("should drop stored entries that are not valid widgets", () => {
    userSettings.settings.set({
      dashboard: { widgets: [...sampleWidgets(), { id: "broken", type: "tokens" }, null] }
    });

    expect(loadedWidgets()).toEqual(sampleWidgets());
  });

  it("should fall back to null when loading fails", () => {
    jest.spyOn(userSettings, "getSetting").mockReturnValue(throwError(() => new Error("boom")));

    expect(loadedWidgets()).toBeNull();
  });

  it("should swallow a failing save so the layout stays usable", () => {
    jest.spyOn(userSettings, "setSetting").mockReturnValue(throwError(() => new Error("boom")));

    let completed = false;
    service.save(sampleWidgets()).subscribe({ complete: () => (completed = true) });

    expect(completed).toBe(true);
  });
});
