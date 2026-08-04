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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { UI_LOCALES } from "@core/locale";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { ThemeService } from "@services/theme/theme.service";
import { UiPreferencesService, UiPreferencesServiceInterface } from "@services/user-settings/ui-preferences.service";

@Component({
  selector: "app-ui-settings",
  imports: [DetailsCardComponent, MatFormFieldModule, MatIconModule, MatSelectModule, MatSlideToggleModule],
  templateUrl: "./ui-settings.component.html",
  styleUrl: "./ui-settings.component.scss"
})
export class UISettingsComponent {
  private readonly themeService = inject(ThemeService);
  private readonly uiPreferencesService: UiPreferencesServiceInterface = inject(UiPreferencesService);
  protected readonly locales = UI_LOCALES;
  protected readonly preferredLocale = this.uiPreferencesService.preferredLocale;
  protected readonly showLoadingUrls = this.uiPreferencesService.showLoadingUrls;
  protected readonly theme = this.themeService.visualTheme;
  protected readonly themeToggleLabel = computed(() =>
    this.theme() === "dark" ? $localize`Switch to light theme` : $localize`Switch to dark theme`
  );

  protected toggleTheme(): void {
    this.themeService.setTheme(this.theme() === "dark" ? "light" : "dark");
  }

  protected setShowLoadingUrls(show: boolean): void {
    this.uiPreferencesService.setShowLoadingUrls(show);
  }

  protected selectLocale(code: string): void {
    this.uiPreferencesService.switchLocale(code);
  }
}
