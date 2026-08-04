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
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatTooltipModule } from "@angular/material/tooltip";
import { UI_LOCALES } from "@core/locale";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import {
  AppearanceService,
  CornerLevel,
  DepthLevel,
  LIGHT_SOURCE_LEVELS,
  LIGHT_SOURCE_STEP_ANGLE,
  LightSourceLevel
} from "@services/appearance/appearance.service";
import { ThemeService } from "@services/theme/theme.service";
import { UiPreferencesService, UiPreferencesServiceInterface } from "@services/user-settings/ui-preferences.service";

@Component({
  selector: "app-ui-settings",
  imports: [
    DetailsCardComponent,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule
  ],
  templateUrl: "./ui-settings.component.html",
  styleUrl: "./ui-settings.component.scss"
})
export class UISettingsComponent {
  private readonly themeService = inject(ThemeService);
  private readonly appearanceService = inject(AppearanceService);
  private readonly uiPreferencesService: UiPreferencesServiceInterface = inject(UiPreferencesService);
  protected readonly locales = UI_LOCALES;
  protected readonly preferredLocale = this.uiPreferencesService.preferredLocale;
  protected readonly showLoadingUrls = this.uiPreferencesService.showLoadingUrls;
  protected readonly theme = this.themeService.visualTheme;
  protected readonly depth = this.appearanceService.depth;
  protected readonly lightSource = this.appearanceService.lightSource;
  protected readonly corners = this.appearanceService.corners;
  protected readonly depthLevels: { value: DepthLevel; label: string }[] = [
    { value: "flat", label: $localize`Flat` },
    { value: "subtle", label: $localize`Subtle` },
    { value: "default", label: $localize`Default` },
    { value: "strong", label: $localize`Strong` },
    { value: "very-strong", label: $localize`Very strong` }
  ];
  // The angle is the whole label: a bare number needs no translation, and the dial itself
  // is named by the card title and the group's legend.
  protected readonly lightSourceLevels: { value: LightSourceLevel; label: string }[] = LIGHT_SOURCE_LEVELS.map(
    (value) => ({ value, label: `${Number(value) * LIGHT_SOURCE_STEP_ANGLE}°` })
  );
  protected readonly cornerLevels: { value: CornerLevel; label: string }[] = [
    { value: "square", label: $localize`Square` },
    { value: "default", label: $localize`Default` },
    { value: "round", label: $localize`Round` },
    { value: "extra-round", label: $localize`Extra round` }
  ];
  // Names the mode the toggle switches to, so it reads as the action it performs.
  protected readonly resetTooltip = $localize`Reset all UI settings to their defaults`;
  protected readonly themeToggleLabel = computed(() =>
    this.theme() === "dark" ? $localize`Switch to light mode` : $localize`Switch to dark mode`
  );

  protected toggleTheme(): void {
    this.themeService.setTheme(this.theme() === "dark" ? "light" : "dark");
  }

  protected resetSettings(): void {
    this.appearanceService.resetToDefaults();
    this.themeService.setTheme("light");
    this.uiPreferencesService.setShowLoadingUrls(false);
    // Last, because a language other than the one running is a full-page navigation,
    // which would cancel the requests above.
    this.uiPreferencesService.switchLocale("en");
  }

  protected selectDepth(level: DepthLevel): void {
    this.appearanceService.setDepth(level);
  }

  protected selectLightSource(level: LightSourceLevel): void {
    this.appearanceService.setLightSource(level);
  }

  protected selectCorners(level: CornerLevel): void {
    this.appearanceService.setCorners(level);
  }

  protected setShowLoadingUrls(show: boolean): void {
    this.uiPreferencesService.setShowLoadingUrls(show);
  }

  protected selectLocale(code: string): void {
    this.uiPreferencesService.switchLocale(code);
  }
}
