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
import { Renderer2, RendererFactory2 } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { throwError } from "rxjs";
import { APP_APPEARANCE_COOKIE_NAME } from "@core/constants";
import { readCookie, writeCookie } from "@core/cookie";
import { AuthService } from "@services/auth/auth.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";

import { AppearanceService, DEFAULT_LIGHT_SOURCE, LIGHT_SOURCE_LEVELS, LIGHT_SOURCE_STEPS } from "./appearance.service";

class DomRendererFactory implements RendererFactory2 {
  createRenderer(): Renderer2 {
    return {
      addClass: (el: Element, name: string) => el.classList.add(name),
      removeClass: (el: Element, name: string) => el.classList.remove(name)
    } as unknown as Renderer2;
  }
}

describe("AppearanceService", () => {
  let service: AppearanceService;
  let authService: MockAuthService;
  let userSettingsService: MockUserSettingsService;
  const html = () => document.documentElement;
  const cachedAppearance = (): Record<string, unknown> =>
    JSON.parse(readCookie(APP_APPEARANCE_COOKIE_NAME) ?? "{}") as Record<string, unknown>;
  const clearCachedAppearance = (): void => {
    document.cookie = `${APP_APPEARANCE_COOKIE_NAME}=; path=/; max-age=0`;
  };

  const create = (): void => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        AppearanceService,
        { provide: RendererFactory2, useClass: DomRendererFactory },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserSettingsService, useClass: MockUserSettingsService }
      ]
    });
    service = TestBed.inject(AppearanceService);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    userSettingsService = TestBed.inject(UserSettingsService) as unknown as MockUserSettingsService;
  };

  beforeEach(() => {
    html().className = "";
    clearCachedAppearance();
    create();
  });

  afterAll(() => {
    html().className = "";
  });

  it("should start on the default levels", () => {
    expect(service.depth()).toBe("default");
    expect(service.lightSource()).toBe(DEFAULT_LIGHT_SOURCE);
    expect(service.corners()).toBe("default");
  });

  it("should apply a picked depth as a class, cache it and store it", () => {
    service.setDepth("strong");

    expect(service.depth()).toBe("strong");
    expect(html().classList.contains("depth-strong")).toBe(true);
    expect(cachedAppearance()["depth"]).toBe("strong");
    expect(userSettingsService.settings()?.depth).toBe("strong");
  });

  it("should apply the deepest depth level", () => {
    service.setDepth("very-strong");

    expect(html().classList.contains("depth-very-strong")).toBe(true);
    expect(userSettingsService.settings()?.depth).toBe("very-strong");
  });

  it("should apply a picked light source", () => {
    service.setLightSource("12");

    expect(html().classList.contains("light-source-12")).toBe(true);
    expect(userSettingsService.settings()?.light_source).toBe("12");
  });

  it("should offer a stop per dial position except the horizontal ones", () => {
    expect(LIGHT_SOURCE_LEVELS).toHaveLength(LIGHT_SOURCE_STEPS - 2);
    expect(LIGHT_SOURCE_LEVELS).not.toContain("0");
    expect(LIGHT_SOURCE_LEVELS).not.toContain(String(LIGHT_SOURCE_STEPS / 2));
    expect(LIGHT_SOURCE_LEVELS[0]).toBe("1");
    expect(LIGHT_SOURCE_LEVELS.at(-1)).toBe(String(LIGHT_SOURCE_STEPS - 1));
  });

  it("should fall back to the default stop for a level off the dial", () => {
    service.applyStoredLightSource(String(LIGHT_SOURCE_STEPS));

    expect(service.lightSource()).toBe(DEFAULT_LIGHT_SOURCE);
    expect(html().classList.contains(`light-source-${DEFAULT_LIGHT_SOURCE}`)).toBe(true);
  });

  it("should put every group back on its default", () => {
    service.setDepth("very-strong");
    service.setLightSource("3");
    service.setCorners("square");

    service.resetToDefaults();

    expect(service.depth()).toBe("default");
    expect(service.lightSource()).toBe(DEFAULT_LIGHT_SOURCE);
    expect(service.corners()).toBe("default");
    expect(html().classList.contains("depth-default")).toBe(true);
    expect(userSettingsService.settings()?.corner_radius).toBe("default");
  });

  it("should apply a picked corner radius", () => {
    service.setCorners("square");

    expect(html().classList.contains("corner-square")).toBe(true);
    expect(userSettingsService.settings()?.corner_radius).toBe("square");
  });

  it("should apply a picked status color level", () => {
    expect(service.statusColors()).toBe("aa");

    service.setStatusColors("aaa");

    expect(service.statusColors()).toBe("aaa");
    expect(html().classList.contains("status-colors-aaa")).toBe(true);
    expect(html().classList.contains("status-colors-aa")).toBe(false);
    expect(userSettingsService.settings()?.status_colors).toBe("aaa");
  });

  it("should apply a stored status color level without writing it back, and fall back on an unknown one", () => {
    service.applyStoredStatusColors("a");

    expect(service.statusColors()).toBe("a");
    expect(html().classList.contains("status-colors-a")).toBe(true);
    expect(userSettingsService.settings()?.status_colors).toBeUndefined();

    service.applyStoredStatusColors("neon");

    expect(service.statusColors()).toBe("aa");
  });

  describe("followTheme", () => {
    const setShowAppearanceSettings = (show: boolean): void =>
      authService.authData.update((data) => ({ ...data!, show_appearance_settings: show }));

    it("should give dark AAA status colors, the default depth and light from 280 degrees while the options are hidden", () => {
      service.setDepth("strong");

      service.followTheme("dark");

      expect(service.statusColors()).toBe("aaa");
      expect(service.depth()).toBe("default");
      expect(service.lightSource()).toBe("14");
      expect(html().classList.contains("status-colors-aaa")).toBe(true);
      expect(html().classList.contains("depth-default")).toBe(true);
      expect(html().classList.contains("light-source-14")).toBe(true);
      expect(userSettingsService.settings()).toEqual(
        expect.objectContaining({ status_colors: "aaa", depth: "default", light_source: "14" })
      );
      expect(cachedAppearance()).toEqual(
        expect.objectContaining({ status_colors: "aaa", depth: "default", light_source: "14" })
      );
    });

    it("should give light AA status colors, subtle depth and the default light source while the options are hidden", () => {
      service.followTheme("dark");

      service.followTheme("light");

      expect(service.statusColors()).toBe("aa");
      expect(service.depth()).toBe("subtle");
      expect(service.lightSource()).toBe(DEFAULT_LIGHT_SOURCE);
      expect(userSettingsService.settings()).toEqual(
        expect.objectContaining({ status_colors: "aa", depth: "subtle", light_source: DEFAULT_LIGHT_SOURCE })
      );
    });

    it("should leave the corners as they are", () => {
      service.setCorners("round");

      service.followTheme("dark");

      expect(service.corners()).toBe("round");
    });

    it("should leave every level alone while the appearance options are shown", () => {
      setShowAppearanceSettings(true);
      service.setStatusColors("a");
      service.setDepth("strong");
      service.setLightSource("12");

      service.followTheme("dark");

      expect(service.statusColors()).toBe("a");
      expect(service.depth()).toBe("strong");
      expect(service.lightSource()).toBe("12");
    });
  });

  it("should put the status colors back on AA with the other groups", () => {
    service.setStatusColors("a");

    service.resetToDefaults();

    expect(service.statusColors()).toBe("aa");
    expect(userSettingsService.settings()?.status_colors).toBe("aa");
  });

  it("should reset only the look and leave the status colors as picked", () => {
    service.setDepth("strong");
    service.setStatusColors("aaa");

    service.resetLook();

    expect(service.depth()).toBe("default");
    expect(service.statusColors()).toBe("aaa");
    expect(userSettingsService.settings()?.status_colors).toBe("aaa");
  });

  it("should replace the previous level of the same group only", () => {
    service.setDepth("flat");
    service.setCorners("round");
    service.setDepth("subtle");

    expect(html().classList.contains("depth-flat")).toBe(false);
    expect(html().classList.contains("depth-subtle")).toBe(true);
    expect(html().classList.contains("corner-round")).toBe(true);
  });

  it("should not store anything while nobody is logged in", () => {
    authService.isAuthenticated.set(false);

    service.setDepth("strong");

    expect(html().classList.contains("depth-strong")).toBe(true);
    expect(userSettingsService.settings()?.depth).toBeUndefined();
  });

  it("should report reset as settled once every write has completed", (done) => {
    service.resetToDefaults().subscribe(() => {
      expect(userSettingsService.settings()?.depth).toBe("default");
      expect(userSettingsService.settings()?.light_source).toBe(DEFAULT_LIGHT_SOURCE);
      expect(userSettingsService.settings()?.corner_radius).toBe("default");
      done();
    });
  });

  it("should still report reset as settled when the write fails", (done) => {
    jest.spyOn(userSettingsService, "setSettings").mockReturnValue(throwError(() => new Error("network error")));

    service.resetToDefaults().subscribe(() => done());
  });

  it("should write depth, corners and light source together in one request", () => {
    const setSettingsSpy = jest.spyOn(userSettingsService, "setSettings");

    service.setPreset("flat", "square", "8");

    expect(setSettingsSpy).toHaveBeenCalledTimes(1);
    expect(setSettingsSpy).toHaveBeenCalledWith({ depth: "flat", corner_radius: "square", light_source: "8" });
    expect(service.depth()).toBe("flat");
    expect(service.corners()).toBe("square");
    expect(service.lightSource()).toBe("8");
  });

  it("should report the preset write as settled once it completes", (done) => {
    service.setPreset("strong", "round", "4").subscribe(() => {
      expect(userSettingsService.settings()?.depth).toBe("strong");
      expect(userSettingsService.settings()?.corner_radius).toBe("round");
      expect(userSettingsService.settings()?.light_source).toBe("4");
      done();
    });
  });

  it("should still report the preset write as settled when it fails", (done) => {
    jest.spyOn(userSettingsService, "setSettings").mockReturnValue(throwError(() => new Error("network error")));

    service.setPreset("strong", "round", "4").subscribe(() => done());
  });

  it("should not write a preset while nobody is logged in", () => {
    authService.isAuthenticated.set(false);
    const setSettingsSpy = jest.spyOn(userSettingsService, "setSettings");

    service.setPreset("flat", "square", "8");

    expect(setSettingsSpy).not.toHaveBeenCalled();
    expect(service.depth()).toBe("flat");
  });

  it("should fall back to the default for an unknown level", () => {
    service.applyStoredDepth("gigantic");
    service.applyStoredCorners(null);

    expect(service.depth()).toBe("default");
    expect(service.corners()).toBe("default");
    expect(html().classList.contains("depth-default")).toBe(true);
  });

  it("should apply a stored level without writing it back", () => {
    service.applyStoredCorners("extra-round");

    expect(service.corners()).toBe("extra-round");
    expect(userSettingsService.settings()?.corner_radius).toBeUndefined();
  });

  it("should initialize from the cached appearance", () => {
    writeCookie(
      APP_APPEARANCE_COOKIE_NAME,
      JSON.stringify({ depth: "flat", light_source: "8", corner_radius: "round", status_colors: "aa" })
    );
    create();

    service.initializeAppearance();

    expect(service.depth()).toBe("flat");
    expect(service.statusColors()).toBe("aa");
    expect(html().classList.contains("status-colors-aa")).toBe(true);
    expect(cachedAppearance()["status_colors"]).toBe("aa");
    expect(service.lightSource()).toBe("8");
    expect(service.corners()).toBe("round");
    expect(html().classList.contains("corner-round")).toBe(true);
  });

  it("should fall back to the defaults for an empty cache value", () => {
    writeCookie(APP_APPEARANCE_COOKIE_NAME, "");
    create();

    service.initializeAppearance();

    expect(service.depth()).toBe("default");
  });

  it("should fall back to the defaults for a malformed cache", () => {
    writeCookie(APP_APPEARANCE_COOKIE_NAME, "{not json");
    create();

    service.initializeAppearance();

    expect(service.depth()).toBe("default");
    expect(html().classList.contains("depth-default")).toBe(true);
  });

  it("should fall back to the defaults for a cache that is not an object", () => {
    writeCookie(APP_APPEARANCE_COOKIE_NAME, "42");
    create();

    service.initializeAppearance();

    expect(service.corners()).toBe("default");
  });

  it("should stamp the default classes when nothing is cached", () => {
    clearCachedAppearance();
    create();

    service.initializeAppearance();

    expect(html().classList.contains("depth-default")).toBe(true);
    expect(html().classList.contains(`light-source-${DEFAULT_LIGHT_SOURCE}`)).toBe(true);
    expect(html().classList.contains("corner-default")).toBe(true);
  });
});
