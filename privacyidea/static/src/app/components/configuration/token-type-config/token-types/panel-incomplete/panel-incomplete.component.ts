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
import { MatIconModule } from "@angular/material/icon";

/** Marks the header of a token type panel that holds an invalid entry, which keeps Save disabled. */
@Component({
  selector: "app-panel-incomplete",
  standalone: true,
  imports: [MatIconModule],
  templateUrl: "./panel-incomplete.component.html",
  styleUrl: "./panel-incomplete.component.scss"
})
export class PanelIncompleteComponent {
  incomplete = input.required<boolean>();
}
