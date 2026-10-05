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
import { Component, computed, inject } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { ThemeService } from "@services/theme/theme.service";

/**
 * Checkbox styled as a round knob that switches light and dark mode; checked means dark. Used by
 * UI Settings and the dashboard appearance widget.
 *
 * ThemeSwitcherComponent is the icon-button form of the same switch, used in the user utils panel.
 */
@Component({
  selector: "app-theme-toggle",
  imports: [MatIcon, MatTooltip],
  templateUrl: "./theme-toggle.component.html",
  styleUrl: "./theme-toggle.component.scss"
})
export class ThemeToggleComponent {
  private readonly themeService = inject(ThemeService);

  protected readonly theme = this.themeService.visualTheme;
  // Names the mode a click switches to, not the current one; serves as both tooltip and aria-label.
  protected readonly label = computed(() =>
    this.theme() === "dark"
      ? $localize`:@@common.switchToLightMode:Switch to light mode`
      : $localize`:@@common.switchToDarkMode:Switch to dark mode`
  );

  protected toggle(): void {
    this.themeService.setTheme(this.theme() === "dark" ? "light" : "dark");
  }
}
