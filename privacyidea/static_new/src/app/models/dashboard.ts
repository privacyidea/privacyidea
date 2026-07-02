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
import { computed, Directive, input, signal, Type } from "@angular/core";
import { PolicyAction } from "@services/auth/policy-actions";

export const DASHBOARD_COLUMNS = 24;

export type WidgetState = "loading" | "ready" | "denied" | "error";

export type WidgetTypeId =
  | "tokens"
  | "token-types"
  | "authentications"
  | "administration"
  | "policies"
  | "events"
  | "subscriptions";

export interface WidgetSize {
  cols: number;
  rows: number;
}

export interface WidgetInstance extends WidgetSize {
  id: string;
  type: WidgetTypeId;
  x: number;
  y: number;
}

@Directive()
export abstract class DashboardWidget {
  readonly instance = input<WidgetInstance>();
  readonly state = signal<WidgetState>("loading");
  readonly loading = computed(() => this.state() === "loading");
  readonly partialLoading = computed(() => false);

  static readonly type: WidgetTypeId;
  static readonly title: string = "";
  static readonly icon: string = "";
  static readonly defaultSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly minSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: Number.POSITIVE_INFINITY };
  static readonly pinned: boolean = false;
  static readonly fixedPosition: { x: number; y: number } | null = null;
  static readonly requiredAction: PolicyAction | null = null;

  abstract reload(): void;
}

export type WidgetComponentType = typeof DashboardWidget & Type<DashboardWidget>;
