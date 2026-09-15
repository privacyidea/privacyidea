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
import { Component, input, output } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";

/**
 * One clickable stop on the dial. `slot` is its index on the 18-stop angle circle
 * ($light-source-steps in styles.scss): 1 to 17 without 9, the two horizontal angles having no
 * stop. A dial need not fill every stop.
 */
export interface LightSourceDialItem {
  slot: number;
  value: string;
  label: string;
}

/**
 * Rotary selector. What a stop stands for is up to the caller: UI Settings maps each to a light
 * source angle, the dashboard appearance widget to a whole appearance preset.
 *
 * Pointer and glow read --dial-angle off <html>, not from `selected`, so they always show the
 * light source in effect; `selected` only marks a stop.
 */
@Component({
  selector: "app-light-source-dial",
  imports: [MatTooltip],
  templateUrl: "./light-source-dial.component.html",
  styleUrl: "./light-source-dial.component.scss"
})
export class LightSourceDialComponent {
  readonly items = input.required<LightSourceDialItem[]>();
  readonly selected = input<string>();
  readonly legend = input.required<string>();
  readonly groupName = input("light-source-dial");
  readonly pick = output<string>();
}
