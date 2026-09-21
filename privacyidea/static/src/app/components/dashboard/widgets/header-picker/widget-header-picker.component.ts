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
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatMenu, MatMenuItem, MatMenuTrigger } from "@angular/material/menu";
import { MatTooltip } from "@angular/material/tooltip";

/** The least a picker needs of a choice: something to store it by, and something to show. */
export interface PickerChoice {
  id: string;
  label: string;
}

/**
 * One choice a widget is read by - the time window it covers, say - shown in the widget frame's header and changed
 * from there.
 *
 * A labelled trigger rather than an icon: the current choice has to be legible without opening anything. It is a menu
 * rather than a toggle group because the header has room for one control, not one per choice.
 */
@Component({
  selector: "app-widget-header-picker",
  standalone: true,
  imports: [MatButton, MatIcon, MatMenu, MatMenuItem, MatMenuTrigger, MatTooltip],
  templateUrl: "./widget-header-picker.component.html",
  styleUrl: "./widget-header-picker.component.scss"
})
export class WidgetHeaderPickerComponent {
  readonly choices = input.required<readonly PickerChoice[]>();
  readonly selected = input.required<PickerChoice>();
  // Also the trigger's accessible name, saying what is being chosen.
  readonly tooltip = input.required<string>();
  readonly icon = input<string>();

  readonly picked = output<string>();
}
