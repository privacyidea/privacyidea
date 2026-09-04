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
import { forkJoin } from "rxjs";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatTooltipModule } from "@angular/material/tooltip";
import { UI_LOCALES } from "@core/locale";
import { LandingPage } from "@core/landing-page";
import {
  LightSourceDialComponent,
  LightSourceDialItem
} from "@components/shared/light-source-dial/light-source-dial.component";
import { ThemeToggleComponent } from "@components/shared/theme-toggle/theme-toggle.component";
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
    LightSourceDialComponent,
    MatButtonModule,
    MatButtonToggleModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule,
    ThemeToggleComponent
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
  protected readonly landingPage = this.uiPreferencesService.landingPage;
  protected readonly availableLandingPages = this.uiPreferencesService.availableLandingPages;
  protected readonly landingPageLabels: Record<LandingPage, string> = {
    dashboard: $localize`:@@nav.dashboard:Dashboard`,
    tokens: $localize`:@@common.token:Token`,
    users: $localize`:@@nav.users:Users`,
    audit: $localize`:@@nav.audit:Audit`
  };
  protected readonly depth = this.appearanceService.depth;
  protected readonly lightSource = this.appearanceService.lightSource;
  protected readonly corners = this.appearanceService.corners;
  protected readonly depthLevels: { value: DepthLevel; label: string }[] = [
    { value: "flat", label: $localize`:@@uiSettings.flat:Flat` },
    { value: "subtle", label: $localize`:@@uiSettings.subtle:Subtle` },
    { value: "default", label: $localize`:@@common.default:Default` },
    { value: "strong", label: $localize`:@@uiSettings.strong:Strong` },
    { value: "very-strong", label: $localize`:@@uiSettings.veryStrong:Very strong` }
  ];
  // One item per angle stop, so slot and value coincide; the label is the bare angle, untranslated.
  protected readonly lightSourceDialItems: LightSourceDialItem[] = LIGHT_SOURCE_LEVELS.map((value) => ({
    slot: Number(value),
    value,
    label: `${Number(value) * LIGHT_SOURCE_STEP_ANGLE}°`
  }));
  protected readonly cornerLevels: { value: CornerLevel; label: string }[] = [
    { value: "square", label: $localize`:@@uiSettings.square:Square` },
    { value: "default", label: $localize`:@@common.default:Default` },
    { value: "round", label: $localize`:@@uiSettings.round:Round` },
    { value: "extra-round", label: $localize`:@@uiSettings.extraRound:Extra round` }
  ];
  protected readonly resetTooltip = $localize`:@@uiSettings.resetUiSettingsToDefaults:Reset UI settings to defaults`;
  protected readonly appearanceHint = $localize`:@@uiSettings.changesHowTheInterfaceLooks:Changes how the interface looks: corner rounding, shadow depth and the direction the light comes from. Saved for your account.`;

  protected resetSettings(): void {
    // Switching locale is a full-page navigation, which would abort the other writes if they
    // were still in flight, so it only runs once they have all settled.
    forkJoin([
      this.appearanceService.resetToDefaults(),
      this.themeService.setTheme("system"),
      this.uiPreferencesService.setShowLoadingUrls(false),
      this.uiPreferencesService.resetLandingPage()
    ]).subscribe(() => this.uiPreferencesService.switchLocale("en"));
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

  protected selectLandingPage(page: LandingPage): void {
    this.uiPreferencesService.setLandingPage(page);
  }
}
