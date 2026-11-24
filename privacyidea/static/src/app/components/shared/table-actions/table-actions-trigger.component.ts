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
import { MatMenuPanel, MatMenuTrigger } from "@angular/material/menu";
import { MatTooltip } from "@angular/material/tooltip";

/**
 * The compact "Actions" icon button that sits next to a table's filter and opens the table's actions
 * as a menu. A table hides it while its actions toolbar is visible and shows it once the table is
 * scrolled (see actions-row-collapse in table.scss, which toggles .table-actions-trigger).
 *
 * The host takes no box of its own, so the button is laid out as a direct child of the filter row.
 */
@Component({
  selector: "app-table-actions-trigger",
  imports: [MatIcon, MatIconButton, MatMenuTrigger, MatTooltip],
  templateUrl: "./table-actions-trigger.component.html",
  styleUrl: "./table-actions-trigger.component.scss"
})
export class TableActionsTriggerComponent {
  /** The menu to open, usually the actionsMenu of the table's actions component. */
  readonly menu = input.required<MatMenuPanel>();
}
