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
import { Component, input } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";

/**
 * A muted info icon that reveals a longer explanation in a tooltip on hover/focus,
 * so extra guidance is available on demand without cluttering the layout. Place it
 * next to a field (e.g. as a `matSuffix`) or a section heading.
 */
@Component({
  selector: "app-info-hint",
  templateUrl: "./info-hint.component.html",
  styleUrls: ["./info-hint.component.scss"],
  imports: [MatIcon, MatIconButton, MatTooltip]
})
export class InfoHintComponent {
  readonly text = input.required<string>();
  readonly ariaLabel = input<string>($localize`More information`);
}
