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
import { computed, Directive, viewChild } from "@angular/core";
import { TableActionsComponent } from "./table-actions.component";

/**
 * Base of the feature components that wrap an app-table-actions (e.g. UserTableActionsComponent). It
 * gives them the one member the table around them needs: the actions menu to hand to its
 * app-table-actions-trigger, as `<app-table-actions-trigger [menu]="featureActions.actionsMenu()" />`.
 */
@Directive()
export abstract class TableActionsHost {
  private readonly tableActions = viewChild.required(TableActionsComponent);
  readonly actionsMenu = computed(() => this.tableActions().menu());
}
