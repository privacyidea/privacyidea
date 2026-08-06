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
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import {
  AppearanceService,
  CornerLevel,
  DEFAULT_LIGHT_SOURCE,
  DepthLevel,
  LIGHT_SOURCE_LEVELS,
  LightSourceLevel
} from "@services/appearance/appearance.service";
import { ThemeService } from "@services/theme/theme.service";
import { AppearanceWidgetComponent } from "./appearance-widget.component";

describe("AppearanceWidgetComponent", () => {
  let fixture: ComponentFixture<AppearanceWidgetComponent>;
  let component: AppearanceWidgetComponent;
  let appearanceService: {
    depth: ReturnType<typeof signal<DepthLevel>>;
    lightSource: ReturnType<typeof signal<LightSourceLevel>>;
    corners: ReturnType<typeof signal<CornerLevel>>;
    setDepth: jest.Mock;
    setLightSource: jest.Mock;
    setCorners: jest.Mock;
    resetToDefaults: jest.Mock;
  };
  let themeService: { visualTheme: ReturnType<typeof signal<"light" | "dark">>; setTheme: jest.Mock };

  const host = (): HTMLElement => fixture.nativeElement;

  const instance: WidgetInstance = { id: "appearance-1", type: "appearance", x: 0, y: 0, cols: 6, rows: 6 };

  beforeEach(async () => {
    appearanceService = {
      depth: signal<DepthLevel>("default"),
      lightSource: signal<LightSourceLevel>("16"),
      corners: signal<CornerLevel>("default"),
      setDepth: jest.fn((level: DepthLevel) => appearanceService.depth.set(level)),
      setLightSource: jest.fn((level: LightSourceLevel) => appearanceService.lightSource.set(level)),
      setCorners: jest.fn((level: CornerLevel) => appearanceService.corners.set(level)),
      resetToDefaults: jest.fn()
    };
    themeService = { visualTheme: signal<"light" | "dark">("light"), setTheme: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [AppearanceWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AppearanceService, useValue: appearanceService },
        { provide: ThemeService, useValue: themeService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AppearanceWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(AppearanceWidgetComponent.type).toBe("appearance");
    expect(AppearanceWidgetComponent.title).toBeTruthy();
    expect(AppearanceWidgetComponent.icon).toBeTruthy();
  });

  it("should be resizable, down to the width its three controls need", () => {
    expect(AppearanceWidgetComponent.defaultSize).toEqual({ cols: 6, rows: 6 });
    expect(AppearanceWidgetComponent.minSize).toEqual({ cols: 6, rows: 6 });
    expect(AppearanceWidgetComponent.maxSize).toEqual({ cols: 12, rows: 8 });
  });

  it("should not gate on a policy action: it only ever touches the current user's own appearance", () => {
    expect(AppearanceWidgetComponent.requiredAction).toBeNull();
  });

  it("should be ready immediately: it has nothing to fetch", () => {
    expect(component.state()).toBe("ready");
  });

  it("should offer exactly one preset per light-source stop", () => {
    const radios = host().querySelectorAll<HTMLInputElement>(".dial__slot input");
    expect(radios).toHaveLength(LIGHT_SOURCE_LEVELS.length);
  });

  it("should check the stop of the light source in effect", () => {
    appearanceService.depth.set("default");
    appearanceService.corners.set("default");
    appearanceService.lightSource.set(DEFAULT_LIGHT_SOURCE);
    fixture.detectChanges();

    const checked = Array.from(host().querySelectorAll<HTMLInputElement>(".dial__slot input")).filter(
      (radio) => radio.checked
    );
    expect(checked).toHaveLength(1);
  });

  it("should follow the light source when depth and corners match no preset", () => {
    // very-strong + square is one of the four pairs the dial itself never applies.
    appearanceService.depth.set("very-strong");
    appearanceService.corners.set("square");
    appearanceService.lightSource.set("12");
    fixture.detectChanges();

    const checked = host().querySelector<HTMLInputElement>(".dial__slot input:checked");

    expect(checked?.closest(".dial__slot")?.className).toContain("dial__slot--12");
  });

  it("should apply the preset's depth, corners and light source together on selection", () => {
    // First in generation order is flat depth with square corners, seven stops before the
    // default light source.
    const radios = host().querySelectorAll<HTMLInputElement>(".dial__slot input");

    radios[0].checked = true;
    radios[0].dispatchEvent(new Event("change"));

    expect(appearanceService.setDepth).toHaveBeenCalledWith("flat");
    expect(appearanceService.setCorners).toHaveBeenCalledWith("square");
    expect(appearanceService.setLightSource).toHaveBeenCalledWith("8");
  });

  it("should sit the all-defaults preset on the default light source", () => {
    appearanceService.depth.set("default");
    appearanceService.corners.set("default");
    appearanceService.lightSource.set(DEFAULT_LIGHT_SOURCE);
    fixture.detectChanges();

    const checked = host().querySelector<HTMLInputElement>(".dial__slot input:checked");

    expect(checked?.closest(".dial__slot")?.className).toContain(`dial__slot--${DEFAULT_LIGHT_SOURCE}`);
  });

  // The knob's own behaviour is covered by ThemeToggleComponent's spec; this checks it is there.
  it("should offer the shared theme knob next to the dial", () => {
    expect(host().querySelector("app-theme-toggle .theme-toggle input")).toBeTruthy();
  });

  it("should reset the appearance and the theme, and nothing else", () => {
    const reset = host().querySelector<HTMLButtonElement>("button");

    reset?.click();

    expect(appearanceService.resetToDefaults).toHaveBeenCalled();
    expect(themeService.setTheme).toHaveBeenCalledWith("light");
  });

  it("should never apply very-strong or flat with the corners they read wrong at", () => {
    const excluded = ["very-strong:square", "very-strong:extra-round", "flat:round", "flat:extra-round"];
    const radios = Array.from(host().querySelectorAll<HTMLInputElement>(".dial__slot input"));

    for (const radio of radios) {
      radio.checked = true;
      radio.dispatchEvent(new Event("change"));

      const depth = appearanceService.setDepth.mock.lastCall?.[0];
      const corner = appearanceService.setCorners.mock.lastCall?.[0];
      expect(excluded).not.toContain(`${depth}:${corner}`);
    }
  });

  it("should do nothing on reload(): there is no data to refresh", () => {
    expect(() => component.reload()).not.toThrow();
    expect(component.state()).toBe("ready");
  });
});
