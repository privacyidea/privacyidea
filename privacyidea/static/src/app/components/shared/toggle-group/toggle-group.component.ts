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
import { Component, computed, input, model, viewChildren } from "@angular/core";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";

/**
 * A single-choice group of Material button toggles for a short, fixed list of options. The toggles share the group's
 * width evenly and clip a long label with an ellipsis, which then shows as a tooltip (the layout rules are keyed on the
 * host class in styles/_material-overrides.scss). Selection follows the radio-group pattern: one Tab stop, arrow keys
 * move and select.
 *
 * `value` and `disabled` make the component usable as a form value control.
 */
@Component({
  selector: "app-toggle-group",
  imports: [MatButtonToggleGroup, MatButtonToggle, TruncationTooltipDirective],
  templateUrl: "./toggle-group.component.html",
  host: { class: "app-toggle-group" }
})
export class ToggleGroupComponent<T> {
  readonly values = input.required<readonly T[]>();
  // Index-aligned with `values`; a missing or empty entry falls back to the value itself.
  readonly labels = input<readonly string[]>();
  // The accessible name of the group.
  readonly groupLabel = input.required<string>();
  readonly disabled = input(false);
  // Hides the check mark of the selected toggle, which saves 30px of label width; the selected label is bold instead.
  readonly hideSelectionIndicator = input(false);
  readonly value = model<T | undefined>();

  private readonly toggles = viewChildren(MatButtonToggle);

  // The one toggle that is a Tab stop: the selected one, or the first while nothing is selected. Material fixes the
  // roving tabindex once, when the group initialises, so toggles added later would all start as Tab stops.
  private readonly tabStop = computed(() => {
    const values = this.values();
    return values.includes(this.value() as T) ? this.value() : values[0];
  });

  protected labelAt(index: number): string {
    return this.labels()?.[index] || String(this.values()[index]);
  }

  protected tabIndexFor(value: T): number {
    return value === this.tabStop() ? 0 : -1;
  }

  /** Moves focus to the selected toggle, or to the first one while nothing is selected. */
  focus(): void {
    (this.toggles().find((toggle) => toggle.checked) ?? this.toggles()[0])?.focus();
  }
}
