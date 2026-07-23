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
import { LOCALE_ID } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { LOCALE_COOKIE_NAME } from "@core/locale";
import { AuthService } from "@services/auth/auth.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { throwError } from "rxjs";
import { LanguageSwitcherComponent } from "./language-switcher.component";

describe("LanguageSwitcherComponent", () => {
  let navigateSpy: jest.SpyInstance;
  let authService: MockAuthService;
  let userSettingsService: MockUserSettingsService;

  interface TestableSwitcher {
    currentLocale: string;
    switchTo: (code: string) => void;
    navigate: (url: string) => void;
  }

  const create = (locale: string): TestableSwitcher => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [LanguageSwitcherComponent],
      providers: [
        { provide: LOCALE_ID, useValue: locale },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserSettingsService, useClass: MockUserSettingsService }
      ]
    });
    const fixture: ComponentFixture<LanguageSwitcherComponent> = TestBed.createComponent(LanguageSwitcherComponent);
    fixture.detectChanges();
    // Members are protected (template-only); access them through the instance for testing.
    const component = fixture.componentInstance as unknown as TestableSwitcher;
    navigateSpy = jest.spyOn(component, "navigate").mockImplementation(() => undefined);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    userSettingsService = TestBed.inject(UserSettingsService) as unknown as MockUserSettingsService;
    return component;
  };

  beforeEach(() => {
    // Clear the locale cookie and reset the URL to a known root between tests.
    document.cookie = `${LOCALE_COOKIE_NAME}=; path=/; max-age=0`;
    window.history.replaceState({}, "", "/");
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates", () => {
    expect(create("en")).toBeTruthy();
  });

  it("reports the compiled locale as current", () => {
    expect(create("de").currentLocale).toBe("de");
    expect(create("zh-Hant").currentLocale).toBe("zh-Hant");
  });

  it("normalizes English region variants to 'en'", () => {
    expect(create("en-US").currentLocale).toBe("en");
    expect(create("en").currentLocale).toBe("en");
  });

  it("switching to another locale sets the cookie and navigates to that bundle", () => {
    create("en").switchTo("de");
    expect(document.cookie).toContain(`${LOCALE_COOKIE_NAME}=de`);
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/");
  });

  it("switching to English navigates to the subpath-less base", () => {
    create("de").switchTo("en");
    expect(document.cookie).toContain(`${LOCALE_COOKIE_NAME}=en`);
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/");
  });

  it("selecting the current locale is a no-op", () => {
    create("de").switchTo("de");
    expect(navigateSpy).not.toHaveBeenCalled();
    expect(document.cookie).not.toContain(`${LOCALE_COOKIE_NAME}=de`);
  });

  it("preserves the current in-app route and query string when switching", () => {
    window.history.replaceState({}, "", "/app/v2/de/tokens/details/OATH0001?foo=bar");
    create("de").switchTo("fr");
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/fr/tokens/details/OATH0001?foo=bar");
  });

  it("maps the route correctly when leaving English (no locale subpath)", () => {
    window.history.replaceState({}, "", "/app/v2/tokens");
    create("en").switchTo("de");
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
  });

  it("stores the language as the user's locale setting when logged in", () => {
    const switcher = create("en");
    authService.isAuthenticated.set(true);

    switcher.switchTo("de");

    expect(userSettingsService.settings()?.["locale"]).toBe("de");
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/");
  });

  it("navigates even when storing the setting fails", () => {
    const switcher = create("en");
    authService.isAuthenticated.set(true);
    jest.spyOn(userSettingsService, "setSetting").mockReturnValue(throwError(() => new Error("boom")));

    switcher.switchTo("de");

    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/");
  });

  it("does not store a setting when nobody is logged in", () => {
    const switcher = create("en");
    authService.isAuthenticated.set(false);
    const setSpy = jest.spyOn(userSettingsService, "setSetting");

    switcher.switchTo("de");

    expect(setSpy).not.toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/");
  });

  it("does not double the locale prefix when a foreign locale segment is in the URL", () => {
    // e.g. the English bundle served in place at a non-English URL after a missing-bundle fallback.
    window.history.replaceState({}, "", "/app/v2/zh-Hant/tokens");
    create("en").switchTo("de");
    expect(navigateSpy).toHaveBeenCalledWith("/app/v2/de/tokens");
  });
});
