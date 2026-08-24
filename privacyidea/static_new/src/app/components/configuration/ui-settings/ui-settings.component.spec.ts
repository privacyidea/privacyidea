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
import { Subject, of } from "rxjs";
import {
  AppearanceService,
  CornerLevel,
  DEFAULT_LIGHT_SOURCE,
  DepthLevel,
  LIGHT_SOURCE_LEVELS,
  LightSourceLevel
} from "@services/appearance/appearance.service";
import { ThemeService } from "@services/theme/theme.service";
import { UiPreferencesService } from "@services/user-settings/ui-preferences.service";
import { MockUiPreferencesService } from "@testing/mock-services/mock-ui-preferences-service";
import { UISettingsComponent } from "./ui-settings.component";

describe("UISettingsComponent", () => {
  let fixture: ComponentFixture<UISettingsComponent>;
  let component: UISettingsComponent;
  let uiPreferencesService: MockUiPreferencesService;
  let themeService: { visualTheme: ReturnType<typeof signal<"light" | "dark">>; setTheme: jest.Mock };
  let appearanceService: {
    depth: ReturnType<typeof signal<DepthLevel>>;
    lightSource: ReturnType<typeof signal<LightSourceLevel>>;
    corners: ReturnType<typeof signal<CornerLevel>>;
    setDepth: jest.Mock;
    resetToDefaults: jest.Mock;
    setLightSource: jest.Mock;
    setCorners: jest.Mock;
  };

  const host = (): HTMLElement => fixture.nativeElement;

  interface TestableSettings {
    preferredLocale: () => string;
    selectLocale: (code: string) => void;
    showLoadingUrls: () => boolean;
    setShowLoadingUrls: (show: boolean) => void;
    depth: () => DepthLevel;
    lightSource: () => LightSourceLevel;
    corners: () => CornerLevel;
    resetSettings: () => void;
    selectDepth: (level: DepthLevel) => void;
    selectLightSource: (level: LightSourceLevel) => void;
    selectCorners: (level: CornerLevel) => void;
  }

  const testable = (): TestableSettings => component as unknown as TestableSettings;

  beforeEach(async () => {
    themeService = { visualTheme: signal<"light" | "dark">("light"), setTheme: jest.fn(() => of(null)) };
    appearanceService = {
      depth: signal<DepthLevel>("default"),
      lightSource: signal<LightSourceLevel>(DEFAULT_LIGHT_SOURCE),
      corners: signal<CornerLevel>("default"),
      resetToDefaults: jest.fn(() => of(null)),
      setDepth: jest.fn((level: DepthLevel) => appearanceService.depth.set(level)),
      setLightSource: jest.fn((level: LightSourceLevel) => appearanceService.lightSource.set(level)),
      setCorners: jest.fn((level: CornerLevel) => appearanceService.corners.set(level))
    };
    await TestBed.configureTestingModule({
      imports: [UISettingsComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: ThemeService, useValue: themeService },
        { provide: AppearanceService, useValue: appearanceService },
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

  // Toggling is covered by ThemeToggleComponent's own spec.
  it("should offer the shared theme knob", () => {
    expect(host().querySelector("app-theme-toggle .theme-toggle input")).toBeTruthy();
  });

  it("should reset every UI setting to its default", () => {
    testable().resetSettings();

    expect(appearanceService.resetToDefaults).toHaveBeenCalled();
    expect(themeService.setTheme).toHaveBeenCalledWith("system");
    expect(uiPreferencesService.setShowLoadingUrls).toHaveBeenCalledWith(false);
    expect(uiPreferencesService.switchLocale).toHaveBeenCalledWith("en");
  });

  // Locale switching is a full-page navigation that would abort the other writes if they were
  // still in flight, so it must not fire until all three have settled.
  it("should not switch locale until the other resets have settled", () => {
    const depthWrite = new Subject<unknown>();
    appearanceService.resetToDefaults.mockReturnValue(depthWrite.asObservable());

    testable().resetSettings();

    expect(uiPreferencesService.switchLocale).not.toHaveBeenCalled();

    depthWrite.next(null);
    depthWrite.complete();

    expect(uiPreferencesService.switchLocale).toHaveBeenCalledWith("en");
  });

  it("should apply a picked depth level", () => {
    testable().selectDepth("flat");

    expect(appearanceService.setDepth).toHaveBeenCalledWith("flat");
    expect(testable().depth()).toBe("flat");
  });

  it("should apply a picked light source", () => {
    testable().selectLightSource("12");

    expect(appearanceService.setLightSource).toHaveBeenCalledWith("12");
    expect(testable().lightSource()).toBe("12");
  });

  // The dial's own rendering is covered by LightSourceDialComponent's spec; this checks the wiring.
  it("should hand the dial one item per light-source stop, keyed by the current value", () => {
    const radios = host().querySelectorAll<HTMLInputElement>(".dial__slot input");

    expect(radios).toHaveLength(LIGHT_SOURCE_LEVELS.length);
    expect(Array.from(radios).filter((radio) => radio.checked)).toHaveLength(1);
  });

  it("should apply the light source turned to on the dial", () => {
    const radios = host().querySelectorAll<HTMLInputElement>(".dial__slot input");

    radios[2].checked = true;
    radios[2].dispatchEvent(new Event("change"));

    expect(appearanceService.setLightSource).toHaveBeenCalledWith(LIGHT_SOURCE_LEVELS[2]);
  });

  it("should apply a picked corner radius", () => {
    testable().selectCorners("square");

    expect(appearanceService.setCorners).toHaveBeenCalledWith("square");
    expect(testable().corners()).toBe("square");
  });

  it("should toggle the pending-request list", () => {
    testable().setShowLoadingUrls(true);

    expect(uiPreferencesService.setShowLoadingUrls).toHaveBeenCalledWith(true);
    expect(testable().showLoadingUrls()).toBe(true);
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
