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
import { provideZonelessChangeDetection, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ThemeService } from "@services/theme/theme.service";
import { UiPreferencesService } from "@services/user-settings/ui-preferences.service";
import { MockUiPreferencesService } from "@testing/mock-services/mock-ui-preferences-service";
import { UISettingsComponent } from "./ui-settings.component";

describe("UISettingsComponent", () => {
  let fixture: ComponentFixture<UISettingsComponent>;
  let component: UISettingsComponent;
  let uiPreferencesService: MockUiPreferencesService;
  let themeService: { visualTheme: ReturnType<typeof signal<"light" | "dark">>; setTheme: jest.Mock };

  interface TestableSettings {
    preferredLocale: () => string;
    theme: () => "light" | "dark";
    selectTheme: (mode: "light" | "dark") => void;
    selectLocale: (code: string) => void;
  }

  const testable = (): TestableSettings => component as unknown as TestableSettings;

  beforeEach(async () => {
    themeService = { visualTheme: signal<"light" | "dark">("light"), setTheme: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [UISettingsComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: ThemeService, useValue: themeService },
        { provide: UiPreferencesService, useClass: MockUiPreferencesService }
      ]
    }).compileComponents();

    uiPreferencesService = TestBed.inject(UiPreferencesService) as unknown as MockUiPreferencesService;
    fixture = TestBed.createComponent(UISettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should show the theme in effect", () => {
    expect(testable().theme()).toBe("light");

    themeService.visualTheme.set("dark");

    expect(testable().theme()).toBe("dark");
  });

  it("should apply a picked theme", () => {
    testable().selectTheme("dark");

    expect(themeService.setTheme).toHaveBeenCalledWith("dark");
  });

  it("should preselect the preferred locale", () => {
    uiPreferencesService.preferredLocale.set("de");

    expect(testable().preferredLocale()).toBe("de");
  });

  it("should hand a picked language to the UI preferences", () => {
    testable().selectLocale("de");

    expect(uiPreferencesService.switchLocale).toHaveBeenCalledWith("de");
  });
});
