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
 * One clickable stop on the dial. `slot` is its position on the shared 18-stop angle
 * circle (see $light-source-steps in styles.scss) -- 1..17, skipping 0 and 9, the two
 * purely horizontal stops every consumer of this dial leaves out. A dial does not have to
 * fill every stop: the appearance widget uses all sixteen, but nothing requires that.
 */
export interface LightSourceDialItem {
  slot: number;
  value: string;
  label: string;
}

/**
 * The rotary light-source selector, factored out of UI Settings so a second dial (the
 * dashboard appearance widget) can reuse the exact same circle instead of a second copy of
 * its Sass. What a stop *means* is entirely up to the caller: UI Settings' items are the
 * angles themselves, the widget's are whole appearance presets that happen to occupy the
 * dial's sixteen stops one-for-one.
 *
 * The pointer and glow read the ambient --dial-angle custom property, the same one
 * html.light-source-* sets on <html>, rather than a locally-scoped variable -- both current
 * consumers apply the selection to that same global setting, so the dial showing the live
 * value is correct, not a leak.
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
