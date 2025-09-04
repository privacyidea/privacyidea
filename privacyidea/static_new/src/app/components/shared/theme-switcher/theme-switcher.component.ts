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
