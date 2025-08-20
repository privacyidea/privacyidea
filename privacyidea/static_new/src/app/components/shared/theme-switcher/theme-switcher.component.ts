import { Component, computed, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
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
  private readonly systemPrefersDark = signal(
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );

  readonly isDark = computed(() => {
    const current = this.themeService.currentTheme();
    return (
      current === "dark" || (current === "system" && this.systemPrefersDark())
    );
  });

  readonly icon = computed<ThemeIcon>(() =>
    this.isDark() ? "light_mode" : "dark_mode"
  );

  constructor(private readonly themeService: ThemeService) {
  }

  toggleTheme(): void {
    this.themeService.setTheme(this.isDark() ? "light" : "dark");
  }
}
