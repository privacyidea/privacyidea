import { CommonModule } from "@angular/common";
import { Component, computed, inject, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ThemeService } from "../../../services/theme/theme.service";

type ThemeIcon = "light_mode" | "dark_mode";

@Component({
  selector: "app-theme-switcher",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: "./theme-switcher.component.html",
  styleUrls: ["./theme-switcher.component.scss"]
})
export class ThemeSwitcherComponent {
  private readonly systemPrefersDark = signal(window.matchMedia("(prefers-color-scheme: dark)").matches);
  private readonly themeService = inject(ThemeService);
  readonly isDark = computed(() => {
    const current = this.themeService.currentTheme();
    return current === "dark" || (current === "system" && this.systemPrefersDark());
  });

  readonly icon = computed<ThemeIcon>(() => (this.isDark() ? "light_mode" : "dark_mode"));

  toggleTheme(): void {
    this.themeService.setTheme(this.isDark() ? "light" : "dark");
  }
}
