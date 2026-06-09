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
import { InputSignal, Type } from "@angular/core";

export const DASHBOARD_COLUMNS = 24;

export interface WidgetSize {
  cols: number;
  rows: number;
}

export interface WidgetInstance {
  id: string;
  type: string;
  x: number;
  y: number;
  cols: number;
  rows: number;
  config?: Record<string, unknown>;
}

export interface DashboardLayout {
  id: string;
  widgets: WidgetInstance[];
}

export interface WidgetDefinition {
  type: string;
  title: string;
  icon: string;
  component: Type<unknown>;
  defaultSize: WidgetSize;
  minSize?: WidgetSize;
  maxSize?: WidgetSize;
  requiredRole?: string;
}

export interface DashboardWidget {
  readonly instance: InputSignal<WidgetInstance | undefined>;
}
