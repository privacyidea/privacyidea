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
import { Component, inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";
import { UI_LOCALES } from "@core/locale";
import { UiPreferencesService, UiPreferencesServiceInterface } from "@services/user-settings/ui-preferences.service";

@Component({
  selector: "app-language-switcher",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  templateUrl: "./language-switcher.component.html"
})
export class LanguageSwitcherComponent {
  private readonly uiPreferencesService: UiPreferencesServiceInterface = inject(UiPreferencesService);
  protected readonly locales = UI_LOCALES;
  protected readonly preferredLocale = this.uiPreferencesService.preferredLocale;

  protected switchTo(code: string): void {
    this.uiPreferencesService.switchLocale(code);
  }
}
