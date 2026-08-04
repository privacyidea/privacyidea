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
import { LOCALE_ID, provideZonelessChangeDetection } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { LOCALE_COOKIE_NAME } from "@core/locale";
import { AppearanceService } from "@services/appearance/appearance.service";
import { AuthService } from "@services/auth/auth.service";
import { ThemeService } from "@services/theme/theme.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { throwError } from "rxjs";
import { UiPreferencesService } from "./ui-preferences.service";

describe("UiPreferencesService", () => {
  let service: UiPreferencesService;
  let authService: MockAuthService;
  let userSettingsService: MockUserSettingsService;
  let themeService: { applyStoredTheme: jest.Mock };
  let appearanceService: {
    applyStoredDepth: jest.Mock;
    applyStoredLightSource: jest.Mock;
    applyStoredCorners: jest.Mock;
  };
  let navigateSpy: jest.SpyInstance;

  const create = (locale: string): void => {
    TestBed.resetTestingModule();
    themeService = { applyStoredTheme: jest.fn() };
    appearanceService = {
      applyStoredDepth: jest.fn(),
      applyStoredLightSource: jest.fn(),
      applyStoredCorners: jest.fn()
    };
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: LOCALE_ID, useValue: locale },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserSettingsService, useClass: MockUserSettingsService },
        { provide: ThemeService, useValue: themeService },
        { provide: AppearanceService, useValue: appearanceService },
        UiPreferencesService
      ]
    });
    service = TestBed.inject(UiPreferencesService);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    userSettingsService = TestBed.inject(UserSettingsService) as unknown as MockUserSettingsService;
    // navigate() is protected (a full-page load); reach it through the instance for testing.
    navigateSpy = jest
      .spyOn(service as unknown as { navigate: (url: string) => void }, "navigate")
      .mockImplementation(() => undefined);
  };

  beforeEach(() => {
    document.cookie = `${LOCALE_COOKIE_NAME}=; path=/; max-age=0`;
    sessionStorage.clear();
    window.history.replaceState({}, "", "/app/v2/tokens");
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should apply the stored theme", () => {
    create("en");
    userSettingsService.settings.set({ theme: "dark" });

    service.sync();

    expect(themeService.applyStoredTheme).toHaveBeenCalledWith("dark");
  });

  it("should leave the theme alone when none is stored", () => {
    create("en");
    userSettingsService.settings.set({});

    service.sync();

    expect(themeService.applyStoredTheme).not.toHaveBeenCalled();
  });

  it("should apply the stored pending-request preference", () => {
    create("en");
    userSettingsService.settings.set({ show_loading_urls: true });

    service.sync();

    expect(service.showLoadingUrls()).toBe(true);
  });

  it("should treat an absent pending-request preference as off", () => {
    create("en");
    userSettingsService.settings.set({});

    service.sync();

    expect(service.showLoadingUrls()).toBe(false);
  });

  it("should store a changed pending-request preference", () => {
    create("en");

    service.setShowLoadingUrls(true);

    expect(service.showLoadingUrls()).toBe(true);
    expect(userSettingsService.settings()?.show_loading_urls).toBe(true);
  });

  it("should apply the stored appearance levels", () => {
    create("en");
    userSettingsService.settings.set({ depth: "flat", light_source: "8", corner_radius: "square" });

    service.sync();

    expect(appearanceService.applyStoredDepth).toHaveBeenCalledWith("flat");
    expect(appearanceService.applyStoredLightSource).toHaveBeenCalledWith("8");
    expect(appearanceService.applyStoredCorners).toHaveBeenCalledWith("square");
  });

  it("should leave the appearance alone when none is stored", () => {
    create("en");
    userSettingsService.settings.set({});

    service.sync();

    expect(appearanceService.applyStoredDepth).not.toHaveBeenCalled();
    expect(appearanceService.applyStoredLightSource).not.toHaveBeenCalled();
    expect(appearanceService.applyStoredCorners).not.toHaveBeenCalled();
  });

  it("should do nothing while nobody is logged in", () => {
    create("en");
    authService.isAuthenticated.set(false);
    userSettingsService.settings.set({ theme: "dark", locale: "de" });

    service.sync();

    expect(themeService.applyStoredTheme).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("should load the bundle of the stored locale and remember the choice", () => {
    create("en");
    userSettingsService.settings.set({ locale: "de" });

    service.sync();

    expect(document.cookie).toContain(`${LOCALE_COOKIE_NAME}=de`);
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
  });

  it("should not navigate when the stored locale is the current one", () => {
    create("de");
    window.history.replaceState({}, "", "/app/v2/de/tokens");
    userSettingsService.settings.set({ locale: "de" });

    service.sync();

    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("should not navigate when the URL already asks for the stored locale", () => {
    // Missing bundle: the URL says "de" but the server served the English one.
    create("en");
    window.history.replaceState({}, "", "/app/v2/de/tokens");
    userSettingsService.settings.set({ locale: "de" });

    service.sync();

    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("should not retry a locale whose bundle did not load", () => {
    // First load: the redirect is attempted and remembered.
    create("en");
    userSettingsService.settings.set({ locale: "de" });
    service.sync();
    expect(navigateSpy).toHaveBeenCalledTimes(1);

    // The bundle was missing, so the app came back up in English at the English URL.
    create("en");
    userSettingsService.settings.set({ locale: "de" });
    service.sync();

    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("should forget the attempt once the locale actually loaded", () => {
    create("en");
    userSettingsService.settings.set({ locale: "de" });
    service.sync();

    create("de");
    userSettingsService.settings.set({ locale: "de" });
    service.sync();

    create("en");
    userSettingsService.settings.set({ locale: "de" });
    service.sync();

    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
  });

  it("should ignore an unknown locale value", () => {
    create("en");
    userSettingsService.settings.set({ locale: "klingon" });

    service.sync();

    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("should ignore a locale that is not a string", () => {
    create("en");
    userSettingsService.settings.set({ locale: 42 });

    service.sync();

    expect(navigateSpy).not.toHaveBeenCalled();
  });

  describe("normalizeLocaleUrl", () => {
    it("should drop a locale segment the running bundle does not match", () => {
      // The URL asks for German, but the server answered with the English bundle.
      create("en");
      window.history.replaceState({}, "", "/app/v2/de/users");

      service.normalizeLocaleUrl();

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/users");
    });

    it("should keep the requested page and its query string", () => {
      create("en");
      window.history.replaceState({}, "", "/app/v2/de/tokens/details/OATH0001?foo=bar");

      service.normalizeLocaleUrl();

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/tokens/details/OATH0001?foo=bar");
    });

    it("should rewrite to the running locale, not to English", () => {
      create("de");
      window.history.replaceState({}, "", "/app/v2/fr/users");

      service.normalizeLocaleUrl();

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/users");
    });

    it("should leave a URL whose segment matches the running bundle alone", () => {
      create("de");
      window.history.replaceState({}, "", "/app/v2/de/users");

      service.normalizeLocaleUrl();

      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("should leave a URL without a locale segment alone", () => {
      create("en");
      window.history.replaceState({}, "", "/app/v2/users");

      service.normalizeLocaleUrl();

      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("should not treat an unknown first segment as a locale", () => {
      create("en");
      window.history.replaceState({}, "", "/app/v2/tokens/details/OATH0001");

      service.normalizeLocaleUrl();

      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("should run for an anonymous visitor as well", () => {
      create("en");
      authService.isAuthenticated.set(false);
      window.history.replaceState({}, "", "/app/v2/de/login");

      service.normalizeLocaleUrl();

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/login");
    });
  });

  describe("preferredLocale", () => {
    it("should report the stored language, even while another bundle runs", () => {
      create("en");
      userSettingsService.settings.set({ locale: "de" });

      expect(service.preferredLocale()).toBe("de");
    });

    it("should fall back to the running bundle without a stored language", () => {
      create("de");
      userSettingsService.settings.set({});

      expect(service.preferredLocale()).toBe("de");
    });

    it("should ignore a stored language that is not a known locale", () => {
      create("en");
      userSettingsService.settings.set({ locale: "klingon" });

      expect(service.preferredLocale()).toBe("en");
    });
  });

  describe("switchLocale", () => {
    it("should set the cookie and load the bundle of the chosen locale", () => {
      create("en");

      service.switchLocale("de");

      expect(document.cookie).toContain(`${LOCALE_COOKIE_NAME}=de`);
      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
    });

    it("should navigate to the subpath-less base when switching to English", () => {
      create("de");
      window.history.replaceState({}, "", "/app/v2/de/tokens");

      service.switchLocale("en");

      expect(document.cookie).toContain(`${LOCALE_COOKIE_NAME}=en`);
      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/tokens");
    });

    it("should store the choice without a page load when the bundle already runs", () => {
      // The way out of a stored preference whose bundle the server does not serve: the app
      // runs another locale, and picking that one has to be storable.
      create("en");
      userSettingsService.settings.set({ locale: "de" });

      service.switchLocale("en");

      expect(userSettingsService.settings()?.["locale"]).toBe("en");
      expect(document.cookie).toContain(`${LOCALE_COOKIE_NAME}=en`);
      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("should forget a pending attempt once its locale is chosen away", () => {
      create("en");
      service.switchLocale("de");
      expect(navigateSpy).toHaveBeenCalledTimes(1);

      // Back in the English bundle (the "de" one was missing): choosing English must clear
      // the attempt, otherwise a later switch to German would be skipped as "already tried".
      create("en");
      service.switchLocale("en");
      service.switchLocale("de");

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
    });

    it("should preserve the in-app route and query string", () => {
      create("de");
      window.history.replaceState({}, "", "/app/v2/de/tokens/details/OATH0001?foo=bar");

      service.switchLocale("fr");

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/fr/tokens/details/OATH0001?foo=bar");
    });

    it("should not double the locale prefix when a foreign locale segment is in the URL", () => {
      // e.g. the English bundle served in place at a non-English URL after a missing-bundle fallback.
      create("en");
      window.history.replaceState({}, "", "/app/v2/zh-Hant/tokens");

      service.switchLocale("de");

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
    });

    it("should store the choice as the locale setting when logged in", () => {
      create("en");

      service.switchLocale("de");

      expect(userSettingsService.settings()?.["locale"]).toBe("de");
      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
    });

    it("should navigate even when storing the setting fails", () => {
      create("en");
      jest.spyOn(userSettingsService, "setSetting").mockReturnValue(throwError(() => new Error("boom")));

      service.switchLocale("de");

      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
    });

    it("should not store a setting while nobody is logged in", () => {
      create("en");
      authService.isAuthenticated.set(false);
      const setSpy = jest.spyOn(userSettingsService, "setSetting");

      service.switchLocale("de");

      expect(setSpy).not.toHaveBeenCalled();
      expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
    });
  });
});
