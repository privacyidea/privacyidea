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
import { TestBed } from "@angular/core/testing";

import { ThemeMode, ThemeService } from "./theme.service";
import { DOCUMENT } from "@angular/common";
import { Renderer2, RendererFactory2 } from "@angular/core";
import { APP_THEME_STORAGE_KEY } from "../../core/constants";

class DomRendererFactory implements RendererFactory2 {
  createRenderer(_: any, __: any): Renderer2 {
    return {
      addClass: (el: Element, name: string) => el.classList.add(name),
      removeClass: (el: Element, name: string) => el.classList.remove(name)
    } as unknown as Renderer2;
  }
}

function setupMatchMedia(prefersDarkInitial: boolean) {
  let listener: ((e: MediaQueryListEvent) => void) | undefined;

  const mql = {
    matches: prefersDarkInitial,
    media: "(prefers-color-scheme: dark)",
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn((_type: string, cb: (e: MediaQueryListEvent) => void) => {
      listener = cb;
    }),
    removeEventListener: jest.fn((_type: string, cb: (e: MediaQueryListEvent) => void) => {
      if (listener === cb) listener = undefined;
    }),
    dispatchEvent: jest.fn()
  } as unknown as MediaQueryList;

  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query: string) => {
      if (query.includes("prefers-color-scheme: dark")) return mql;
      return {
        matches: false,
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      } as unknown as MediaQueryList;
    }
  });

  const emitChange = (matches: boolean) => {
    (mql as any).matches = matches;
    if (listener) listener({ matches } as MediaQueryListEvent);
  };

  return { mql, emitChange };
}

describe("ThemeService", () => {
  let service: ThemeService;
  let htmlEl: HTMLHtmlElement;

  beforeEach(() => {
    localStorage.clear();
    jest.restoreAllMocks();

    htmlEl = document.documentElement as HTMLHtmlElement;

    TestBed.configureTestingModule({
      providers: [
        { provide: DOCUMENT, useValue: document },
        { provide: RendererFactory2, useClass: DomRendererFactory },
        ThemeService
      ]
    });

    service = TestBed.inject(ThemeService);
  });

  it("initializeTheme() reads saved theme and applies it", () => {
    localStorage.setItem(APP_THEME_STORAGE_KEY, "dark");
    setupMatchMedia(false);

    service.initializeTheme();

    expect(service.currentTheme()).toBe<ThemeMode>("dark");
    expect(htmlEl.classList.contains("dark")).toBe(true);
    expect(htmlEl.classList.contains("light")).toBe(false);
    expect(htmlEl.classList.contains("system")).toBe(false);
  });

  it("initializeTheme() defaults to 'system' when no saved theme", () => {
    const { mql } = setupMatchMedia(true);

    service.initializeTheme();

    expect(service.currentTheme()).toBe("system");
    expect(htmlEl.classList.contains("system")).toBe(true);
    expect(htmlEl.classList.contains("dark")).toBe(true);
    expect(htmlEl.classList.contains("light")).toBe(false);

    expect((mql as any).addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("setTheme('light') applies classes, updates storage and currentTheme", () => {
    setupMatchMedia(false);

    service.setTheme("light");

    expect(service.currentTheme()).toBe("light");
    expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe("light");
    expect(htmlEl.classList.contains("light")).toBe(true);
    expect(htmlEl.classList.contains("dark")).toBe(false);
    expect(htmlEl.classList.contains("system")).toBe(false);
  });

  it("setTheme('dark') applies classes and overwrites any previous", () => {
    setupMatchMedia(false);

    service.setTheme("light");
    service.setTheme("dark");

    expect(service.currentTheme()).toBe("dark");
    expect(htmlEl.classList.contains("dark")).toBe(true);
    expect(htmlEl.classList.contains("light")).toBe(false);
    expect(htmlEl.classList.contains("system")).toBe(false);
  });

  it("setTheme('system') syncs with current OS preference and listens for changes", () => {
    const { mql, emitChange } = setupMatchMedia(false);

    service.setTheme("system");

    expect(service.currentTheme()).toBe("system");
    expect(htmlEl.classList.contains("system")).toBe(true);
    expect(htmlEl.classList.contains("light")).toBe(true);
    expect(htmlEl.classList.contains("dark")).toBe(false);

    emitChange(true);

    expect(htmlEl.classList.contains("dark")).toBe(true);
    expect(htmlEl.classList.contains("light")).toBe(false);

    expect((mql as any).addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("leaves system mode: removes the media query listener", () => {
    const { mql } = setupMatchMedia(true);

    service.setTheme("system");
    service.setTheme("dark");

    expect((mql as any).removeEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function)
    );
  });

  it("always writes the theme to localStorage", () => {
    setupMatchMedia(false);

    service.setTheme("dark");
    expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe("dark");

    service.setTheme("system");
    expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe("system");
  });
});
