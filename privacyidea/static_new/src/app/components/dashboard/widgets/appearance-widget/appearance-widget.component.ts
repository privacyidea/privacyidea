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

// Depth and corner radius each have their own scale (5 depths, 4 corner radii), so pairing
// every depth with every corner gives 5 * 4 = 20 combinations -- one more than the dial has
// stops for (LIGHT_SOURCE_LEVELS, 16). Four of those twenty are left out: very-strong depth
// casts a shadow heavy enough that it reads wrong at either end of the corner scale (square
// or extra-round), and flat depth -- a hairline ring, no shadow at all -- has nothing left
// to distinguish it from a corner already rounded enough to be its own shape (round or
// extra-round). Leaving those four out brings the count to exactly sixteen, so every dial
// stop carries one preset with none left over and none doubled up.
const EXCLUDED_PAIRS = new Set<string>([
  "very-strong:square",
  "very-strong:extra-round",
  "flat:round",
  "flat:extra-round"
]);

const DEPTH_CORNER_PAIRS: readonly Omit<AppearancePreset, "lightSource">[] = DEPTH_LEVELS.flatMap((depth) =>
  CORNER_LEVELS.filter((corner) => !EXCLUDED_PAIRS.has(`${depth}:${corner}`)).map((corner) => ({ depth, corner }))
);

// The pairs walk the two scales in order, but which stop that order starts on is arbitrary,
// so it is turned until the all-defaults pair sits on the default light source: the stop the
// app itself starts on, so an untouched appearance shows the dial already pointing at it.
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
 * A dashboard shortcut for the depth + corner-radius + light-source trio of UI Settings,
 * reusing its rotary dial. Turning the dial does not just change the light direction: each
 * of its sixteen stops is a whole appearance preset (see APPEARANCE_PRESETS above), so one
 * click applies all three settings at once. Like UI Settings itself this changes the live,
 * app-wide appearance for the current user -- it is a second control surface for the same
 * global setting, not an isolated preview.
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
  // The dial is a fixed circle, so the widget grows by spreading its row rather than by
  // scaling anything: the minimum is the width the three controls need side by side.
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
  // the full UI Settings page can still set.
  protected readonly selected = computed(() => this.currentPreset()?.lightSource);

  constructor() {
    super();
    // Nothing is fetched: every value this widget shows comes from AppearanceService's
    // already-live signals.
    this.state.set("ready");
  }

  reload(): void {
    // No data to refresh -- the dial already reflects the live appearance reactively.
  }

  // The widget's own two concerns only: the language and the pending-request list it does not
  // offer are left where they are, so this undoes what the widget itself can do and no more.
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
