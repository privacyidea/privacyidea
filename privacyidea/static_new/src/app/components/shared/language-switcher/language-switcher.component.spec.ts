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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { UiPreferencesService } from "@services/user-settings/ui-preferences.service";
import { MockUiPreferencesService } from "@testing/mock-services/mock-ui-preferences-service";
import { LanguageSwitcherComponent } from "./language-switcher.component";

describe("LanguageSwitcherComponent", () => {
  let fixture: ComponentFixture<LanguageSwitcherComponent>;
  let uiPreferencesService: MockUiPreferencesService;

  interface TestableSwitcher {
    preferredLocale: () => string;
    switchTo: (code: string) => void;
  }

  const create = (locale: string): TestableSwitcher => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [LanguageSwitcherComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: UiPreferencesService, useClass: MockUiPreferencesService }
      ]
    });
    uiPreferencesService = TestBed.inject(UiPreferencesService) as unknown as MockUiPreferencesService;
    uiPreferencesService.preferredLocale.set(locale);
    fixture = TestBed.createComponent(LanguageSwitcherComponent);
    fixture.detectChanges();
    // Members are protected (template-only); access them through the instance for testing.
    return fixture.componentInstance as unknown as TestableSwitcher;
  };

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates", () => {
    expect(create("en")).toBeTruthy();
  });

  it("marks the preferred locale as the selected one", () => {
    expect(create("de").preferredLocale()).toBe("de");
    expect(create("zh-Hant").preferredLocale()).toBe("zh-Hant");
  });

  it("hands a selected language to the UI preferences", () => {
    create("en").switchTo("de");

    expect(uiPreferencesService.switchLocale).toHaveBeenCalledWith("de");
  });
});
