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
      JSON.stringify({ depth: "flat", light_source: "8", corner_radius: "round" })
    );
    create();

    service.initializeAppearance();

    expect(service.depth()).toBe("flat");
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
