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
import { Component, computed, input, viewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatMenu, MatMenuModule, MatMenuPanel } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";
import { OverflowNavDirective } from "../directives/overflow-nav/overflow-nav.directive";

export type TableActionTone = "primary" | "secondary" | "delete-primary" | "delete-secondary";

/** Where an action is offered: as a button in the toolbar and an item in the menu, or in the menu only. */
export type TableActionPlacement = "toolbar-and-menu" | "menu";

/** One action of a table's actions toolbar, drawn once as a toolbar button and once as a menu item. */
export interface TableAction {
  /** Identifies the action across re-renders. */
  id: string;
  label: string;
  tone: TableActionTone;
  /** Width tier of the toolbar button (button-width-*). */
  width: "m" | "l";
  /** Material ligature drawn in the toolbar button and, unless menuIcon is set, in the menu item. */
  icon?: string;
  /** Ligature of the menu item where it differs from the toolbar button's. */
  menuIcon?: string;
  /** Icon-font class (e.g. ms--database) that draws the icon in the button and the menu item. */
  fontIcon?: string;
  /** Extra classes on the toolbar button's icon only, such as its spacing. */
  iconClass?: string;
  /** Draws the toolbar button's icon with a small "+" badge, as for actions that create something. */
  badge?: boolean;
  /** Adds clear space between the badge and the label of the toolbar button. */
  spacedBadge?: boolean;
  /** The toolbar button stays visible while the rest of the toolbar folds into the "More" menu. */
  pinned?: boolean;
  /** Defaults to true. */
  visible?: boolean;
  disabled?: boolean;
  placement?: TableActionPlacement;
  tooltip?: string;
  /** Opens this menu instead of running the action. */
  submenu?: MatMenuPanel;
  run?: () => void;
}

/**
 * The actions toolbar of a table: a row of buttons above the table that folds into a "More" menu when
 * it does not fit, plus the equivalent mat-menu behind the compact actions trigger
 * (app-table-actions-trigger) that replaces the row once the table is scrolled.
 *
 * A feature describes its actions once as TableAction[] and gets both renderings, with the layout,
 * the button styling and the overflow handling in one place. Anything that is not a plain action goes
 * into the default content slot, which projects at the start of the toolbar (e.g. a realm select).
 * The mat-menu is exposed as `menu` for the trigger; feature components extend TableActionsHost to
 * pass it on.
 */
@Component({
  selector: "app-table-actions",
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule, OverflowNavDirective],
  templateUrl: "./table-actions.component.html",
  styleUrl: "./table-actions.component.scss"
})
export class TableActionsComponent {
  readonly actions = input.required<TableAction[]>();
  /** "compact" is a wrapping row with an 8px gap; "roomy" a single row with a 16px gap and centred items. */
  readonly layout = input<"compact" | "roomy">("compact");
  /** Leaves the usual space below the toolbar; off where the row that holds it provides that space. */
  readonly spaced = input(true);
  /** Lets the buttons wrap onto further lines when they do not fit; off keeps them on a single line. */
  readonly wrap = input(true);
  /** Draws no toolbar at all (and so no space below it) while none of its actions is visible. */
  readonly collapseWhenEmpty = input(false);

  readonly menu = viewChild.required(MatMenu);

  protected readonly menuActions = computed(() => this.actions().filter((action) => action.visible !== false));
  protected readonly toolbarActions = computed(() =>
    this.menuActions().filter((action) => action.placement !== "menu")
  );

  protected buttonClass(action: TableAction): string {
    return `action-button-${action.tone} button-width-${action.width}`;
  }

  protected buttonIconClass(action: TableAction): string {
    return [action.fontIcon, action.iconClass].filter(Boolean).join(" ");
  }
}
