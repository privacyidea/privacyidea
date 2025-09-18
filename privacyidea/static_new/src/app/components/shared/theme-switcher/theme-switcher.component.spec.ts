/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ThemeSwitcherComponent } from "./theme-switcher.component";
import { signal } from "@angular/core";
import { ThemeService } from "../../../services/theme/theme.service";


describe("ThemeSwitcherComponent", () => {
  let mockThemeService: {
    currentTheme: ReturnType<typeof signal<"light" | "dark" | "system">>;
    setTheme: jest.Mock;
  };

  const setMatchMedia = (prefersDark: boolean) => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: prefersDark && query.includes("prefers-color-scheme: dark"),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });
  };

  const create = (systemPrefersDark: boolean, theme: "light" | "dark" | "system") => {
    setMatchMedia(systemPrefersDark);
    mockThemeService.currentTheme.set(theme);

    const fixture: ComponentFixture<ThemeSwitcherComponent> =
      TestBed.createComponent(ThemeSwitcherComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    return { fixture, component };
  };

  beforeEach(async () => {
    mockThemeService = {
      currentTheme: signal<"light" | "dark" | "system">("light"),
      setTheme: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [ThemeSwitcherComponent],
      providers: [{ provide: ThemeService, useValue: mockThemeService }]
    }).compileComponents();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates", () => {
    const { component } = create(false, "light");
    expect(component).toBeTruthy();
  });

  it("icon is 'dark_mode' when light theme; 'light_mode' when dark theme", () => {
    let ctx = create(false, "light");
    expect(ctx.component.isDark()).toBe(false);
    expect(ctx.component.icon()).toBe("dark_mode");

    ctx = create(false, "dark");
    expect(ctx.component.isDark()).toBe(true);
    expect(ctx.component.icon()).toBe("light_mode");
  });

  it("system theme follows systemPrefersDark", () => {
    let ctx = create(true, "system");
    expect(ctx.component.isDark()).toBe(true);
    expect(ctx.component.icon()).toBe("light_mode");

    ctx = create(false, "system");
    expect(ctx.component.isDark()).toBe(false);
    expect(ctx.component.icon()).toBe("dark_mode");
  });

  it("toggleTheme sets opposite theme relative to isDark()", () => {
    let ctx = create(false, "dark");
    ctx.component.toggleTheme();
    expect(mockThemeService.setTheme).toHaveBeenCalledWith("light");

    jest.clearAllMocks();

    ctx = create(false, "light");
    ctx.component.toggleTheme();
    expect(mockThemeService.setTheme).toHaveBeenCalledWith("dark");

    jest.clearAllMocks();

    ctx = create(true, "system");
    ctx.component.toggleTheme();
    expect(mockThemeService.setTheme).toHaveBeenCalledWith("light");

    jest.clearAllMocks();

    ctx = create(false, "system");
    ctx.component.toggleTheme();
    expect(mockThemeService.setTheme).toHaveBeenCalledWith("dark");
  });
});