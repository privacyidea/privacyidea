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
import { Directive, input, Type } from "@angular/core";

export const DASHBOARD_COLUMNS = 24;

export interface WidgetSize {
  cols: number;
  rows: number;
}

export interface WidgetInstance extends WidgetSize {
  id: string;
  type: string;
  x: number;
  y: number;
}

@Directive()
export abstract class DashboardWidget {
  readonly instance = input<WidgetInstance>();

  static readonly type: string = "";
  static readonly title: string = "";
  static readonly icon: string = "";
  static readonly defaultSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly minSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: Number.POSITIVE_INFINITY };
}

export type WidgetComponentType = typeof DashboardWidget & Type<DashboardWidget>;
