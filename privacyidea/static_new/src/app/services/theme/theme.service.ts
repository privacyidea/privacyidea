// src/app/services/theme/theme.service.ts
import { DOCUMENT } from "@angular/common";
import { Injectable, Renderer2, RendererFactory2, inject, signal } from "@angular/core";
import { APP_THEME_STORAGE_KEY } from "../../core/constants";

export type ThemeMode = "light" | "dark" | "system";

@Injectable({
  providedIn: "root"
})
export class ThemeService {
  private renderer: Renderer2;
  private htmlElement: HTMLHtmlElement;
  private mediaQueryListener?: (event: MediaQueryListEvent) => void;
  public readonly currentTheme = signal<ThemeMode>("system");
  private readonly visualTheme = signal<"light" | "dark">("light");

  constructor(private rendererFactory: RendererFactory2) {
    this.renderer = this.rendererFactory.createRenderer(null, null);
    this.htmlElement = inject(DOCUMENT).documentElement as HTMLHtmlElement;
  }

  public initializeTheme(): void {
    const savedTheme = localStorage.getItem(APP_THEME_STORAGE_KEY) as ThemeMode;
    this.setTheme(savedTheme || "system");
  }

  /**
   * Sets the theme, updates local storage, and applies the corresponding
   * classes to the HTML element.
   * @param themeMode The themeMode to set ('light', 'dark', or 'system').
   */
  public setTheme(themeMode: ThemeMode): void {
    const oldThemes: ThemeMode[] = ["light", "dark", "system"];
    oldThemes.forEach((t) => this.renderer.removeClass(this.htmlElement, t));

    this.currentTheme.set(themeMode);
    localStorage.setItem(APP_THEME_STORAGE_KEY, themeMode);

    this.removeSystemThemeListener();
    this.applyTheme(themeMode);
  }

  private applyTheme(theme: ThemeMode): void {
    if (theme === "system") {
      this.renderer.removeClass(this.htmlElement, "light");
      this.renderer.removeClass(this.htmlElement, "dark");
      this.renderer.addClass(this.htmlElement, "system");

      this.syncWithSystemTheme();
      this.addSystemThemeListener();
    } else {
      this.renderer.removeClass(this.htmlElement, "light");
      this.renderer.removeClass(this.htmlElement, "dark");
      this.renderer.addClass(this.htmlElement, theme);

      this.visualTheme.set(theme);
    }
  }

  private syncWithSystemTheme(): void {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
    const newVisualTheme = prefersDark.matches ? "dark" : "light";
    this.renderer.addClass(this.htmlElement, newVisualTheme);
    this.visualTheme.set(newVisualTheme);
  }

  private addSystemThemeListener(): void {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
    this.mediaQueryListener = (event: MediaQueryListEvent) => {
      const newVisualTheme = event.matches ? "dark" : "light";
      this.renderer.removeClass(this.htmlElement, newVisualTheme === "light" ? "dark" : "light");
      this.renderer.addClass(this.htmlElement, newVisualTheme);
      this.visualTheme.set(newVisualTheme);
    };
    prefersDark.addEventListener("change", this.mediaQueryListener);
  }

  private removeSystemThemeListener(): void {
    if (this.mediaQueryListener) {
      window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", this.mediaQueryListener);
      this.mediaQueryListener = undefined;
    }
  }
}
