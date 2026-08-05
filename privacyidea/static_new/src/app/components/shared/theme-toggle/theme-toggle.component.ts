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
 * The round light/dark knob of the UI settings, shared with the dashboard appearance widget
 * so both wear the same control rather than two takes on it. It presses in when dark mode is
 * on -- the raised and recessed halves of the depth scale on one element, so the knob shows
 * the state it is in the same way the rest of the app shows depth.
 *
 * Distinct from ThemeSwitcherComponent, the plain icon button the self-service utility panel
 * puts in a toolbar, where a 72px knob would not fit.
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
  // Names the mode the toggle switches to, so it reads as the action it performs.
  protected readonly label = computed(() =>
    this.theme() === "dark" ? $localize`Switch to light mode` : $localize`Switch to dark mode`
  );

  protected toggle(): void {
    this.themeService.setTheme(this.theme() === "dark" ? "light" : "dark");
  }
}
