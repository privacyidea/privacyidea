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
import { AuthService } from "@services/auth/auth.service";
import { ThemeService } from "@services/theme/theme.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { UiPreferencesService } from "./ui-preferences.service";

describe("UiPreferencesService", () => {
  let service: UiPreferencesService;
  let authService: MockAuthService;
  let userSettingsService: MockUserSettingsService;
  let themeService: { applyStoredTheme: jest.Mock };
  let navigateSpy: jest.SpyInstance;

  const create = (locale: string): void => {
    TestBed.resetTestingModule();
    themeService = { applyStoredTheme: jest.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: LOCALE_ID, useValue: locale },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserSettingsService, useClass: MockUserSettingsService },
        { provide: ThemeService, useValue: themeService },
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
});
