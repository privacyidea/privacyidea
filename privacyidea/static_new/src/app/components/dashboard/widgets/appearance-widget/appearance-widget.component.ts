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
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import {
  LightSourceDialComponent,
  LightSourceDialItem
} from "@components/shared/light-source-dial/light-source-dial.component";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import {
  AppearanceService,
  CORNER_LEVELS,
  CornerLevel,
  DEFAULT_LIGHT_SOURCE,
  DEPTH_LEVELS,
  DepthLevel,
  LIGHT_SOURCE_LEVELS,
  LightSourceLevel
} from "@services/appearance/appearance.service";
import { ThemeService } from "@services/theme/theme.service";
import { ThemeToggleComponent } from "@components/shared/theme-toggle/theme-toggle.component";

interface AppearancePreset {
  depth: DepthLevel;
  corner: CornerLevel;
  lightSource: LightSourceLevel;
}

// 5 depths * 4 corner radii = 20 pairs, four more than the dial's 16 stops
// (LIGHT_SOURCE_LEVELS). The four left out read wrong: very-strong casts too heavy a shadow for
// either end of the corner scale, and flat, with no shadow at all, leaves a strongly rounded
// corner nothing to set it apart. That leaves exactly one preset per stop.
const EXCLUDED_PAIRS = new Set<string>([
  "very-strong:square",
  "very-strong:extra-round",
  "flat:round",
  "flat:extra-round"
]);

const DEPTH_CORNER_PAIRS: readonly Omit<AppearancePreset, "lightSource">[] = DEPTH_LEVELS.flatMap((depth) =>
  CORNER_LEVELS.filter((corner) => !EXCLUDED_PAIRS.has(`${depth}:${corner}`)).map((corner) => ({ depth, corner }))
);

// The pairs walk the two scales in order, which leaves the stop that order starts on
// arbitrary. Turn it until the all-defaults pair sits on the default light source, so an
// untouched appearance shows the dial already pointing at it.
const DIAL_ROTATION =
  (LIGHT_SOURCE_LEVELS.indexOf(DEFAULT_LIGHT_SOURCE) -
    DEPTH_CORNER_PAIRS.findIndex((pair) => pair.depth === "default" && pair.corner === "default") +
    LIGHT_SOURCE_LEVELS.length) %
  LIGHT_SOURCE_LEVELS.length;

const APPEARANCE_PRESETS: readonly AppearancePreset[] = DEPTH_CORNER_PAIRS.map((pair, index) => ({
  ...pair,
  lightSource: LIGHT_SOURCE_LEVELS[(index + DIAL_ROTATION) % LIGHT_SOURCE_LEVELS.length]
}));

const DEPTH_LABELS: Record<DepthLevel, string> = {
  flat: $localize`flat`,
  subtle: $localize`subtle`,
  default: $localize`default`,
  strong: $localize`strong`,
  "very-strong": $localize`very strong`
};

const CORNER_LABELS: Record<CornerLevel, string> = {
  square: $localize`square`,
  default: $localize`default`,
  round: $localize`round`,
  "extra-round": $localize`extra-round`
};

function presetLabel(preset: AppearancePreset): string {
  return $localize`${DEPTH_LABELS[preset.depth]} depth, ${CORNER_LABELS[preset.corner]} corners`;
}

/**
 * Dashboard shortcut for the depth, corner-radius and light-source settings. Each of the dial's
 * sixteen stops is a whole appearance preset (APPEARANCE_PRESETS above), so one click applies
 * all three at once, live and app-wide for the current user rather than as a preview.
 */
@Component({
  selector: "app-appearance-widget",
  imports: [LightSourceDialComponent, MatIcon, MatIconButton, MatTooltip, ThemeToggleComponent],
  templateUrl: "./appearance-widget.component.html",
  styleUrl: "./appearance-widget.component.scss"
})
export class AppearanceWidgetComponent extends DashboardWidget {
  static override readonly type = "appearance";
  static override readonly title = $localize`Appearance`;
  static override readonly icon = "palette";
  // The dial is a fixed circle, so the widget grows by spreading its row. The minimum is the
  // width the three controls need side by side.
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 6 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 6 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 8 };

  private readonly appearanceService = inject(AppearanceService);
  private readonly themeService = inject(ThemeService);

  protected readonly resetTooltip = $localize`Reset appearance to defaults`;

  protected readonly items: LightSourceDialItem[] = APPEARANCE_PRESETS.map((preset) => ({
    slot: Number(preset.lightSource),
    value: preset.lightSource,
    label: presetLabel(preset)
  }));

  private readonly currentPreset = computed<AppearancePreset | undefined>(() =>
    APPEARANCE_PRESETS.find(
      (preset) =>
        preset.depth === this.appearanceService.depth() &&
        preset.corner === this.appearanceService.corners() &&
        preset.lightSource === this.appearanceService.lightSource()
    )
  );

  // No stop is marked when the live appearance is one of the pairs the dial leaves out, which
  // UI Settings can still set.
  protected readonly selected = computed(() => this.currentPreset()?.lightSource);

  constructor() {
    super();
    // Nothing to fetch: every value comes from AppearanceService's live signals.
    this.state.set("ready");
  }

  reload(): void {
    // No data to refresh; the dial follows AppearanceService's signals.
  }

  // Only what this widget controls: the language and the pending-request list are left alone.
  protected resetAppearance(): void {
    this.appearanceService.resetToDefaults();
    this.themeService.setTheme("light");
  }

  protected selectPreset(lightSource: string): void {
    const preset = APPEARANCE_PRESETS.find((candidate) => candidate.lightSource === lightSource);
    if (!preset) {
      return;
    }
    this.appearanceService.setDepth(preset.depth);
    this.appearanceService.setCorners(preset.corner);
    this.appearanceService.setLightSource(preset.lightSource);
  }
}
