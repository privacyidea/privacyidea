import { DOCUMENT } from '@angular/common';
import {
  Inject,
  Injectable,
  Renderer2,
  RendererFactory2,
  signal,
} from '@angular/core';

export type Theme = 'light' | 'dark' | 'system';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private renderer: Renderer2;
  private htmlElement: HTMLHtmlElement;
  private mediaQueryListener?: (event: MediaQueryListEvent) => void;
  currentTheme = signal<Theme>('system');

  constructor(
    private rendererFactory: RendererFactory2,
    @Inject(DOCUMENT) private document: Document,
  ) {
    this.renderer = this.rendererFactory.createRenderer(null, null);

    this.htmlElement = this.document.documentElement as HTMLHtmlElement;
    this.loadInitialTheme();
  }

  setTheme(theme: Theme): void {
    const oldThemes: Theme[] = ['light', 'dark', 'system'];

    oldThemes.forEach((t) => {
      this.renderer.removeClass(this.htmlElement, t);
    });

    this.renderer.removeClass(this.htmlElement, 'light');
    this.renderer.removeClass(this.htmlElement, 'dark');

    if (this.mediaQueryListener) {
      window
        .matchMedia('(prefers-color-scheme: dark)')
        .removeEventListener('change', this.mediaQueryListener);
      this.mediaQueryListener = undefined;
    }

    this.renderer.addClass(this.htmlElement, theme);
    this.currentTheme.set(theme);
    localStorage.setItem('appTheme', theme);

    if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

      if (prefersDark.matches) {
        this.renderer.addClass(this.htmlElement, 'dark');
      } else {
        this.renderer.addClass(this.htmlElement, 'light');
      }

      this.mediaQueryListener = (event: MediaQueryListEvent) => {
        if (event.matches) {
          this.renderer.addClass(this.htmlElement, 'dark');
          this.renderer.removeClass(this.htmlElement, 'light');
        } else {
          this.renderer.addClass(this.htmlElement, 'light');
          this.renderer.removeClass(this.htmlElement, 'dark');
        }
      };
      prefersDark.addEventListener('change', this.mediaQueryListener);
    } else {
      this.renderer.addClass(this.htmlElement, theme);
    }
  }

  private loadInitialTheme(): void {
    const savedTheme = localStorage.getItem('appTheme') as Theme;
    if (savedTheme) {
      this.setTheme(savedTheme);
    } else {
      this.setTheme('system');
    }
  }
}
