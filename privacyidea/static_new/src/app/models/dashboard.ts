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
  | "subscriptions"
  | "certificate-health"
  | "resolver-timing"
  | "notification-delivery"
  | "conditional-access";

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
  readonly refreshFailed = computed(() => false);

  static readonly type: WidgetTypeId;
  static readonly title: string = "";
  static readonly icon: string = "";
  static readonly headerIcon: Type<unknown> | null = null;
  static readonly defaultSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly minSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: Number.POSITIVE_INFINITY };
  // Where the widget's title links to, for a widget that summarizes one page. Null leaves the title as plain text.
  static readonly titleLink: string | null = null;
  static readonly pinned: boolean = false;
  static readonly fixedPosition: { x: number; y: number } | null = null;
  // The right(s) a widget needs to be offered at all. A list means any one of them is enough, for a widget that
  // summarizes several separately-governed areas: it then shows only the parts the admin may read.
  static readonly requiredAction: PolicyAction | PolicyAction[] | null = null;
  static readonly titleLink: string | null = null;
  static readonly titleLinkAction: PolicyAction | null = null;

  abstract reload(): void;
}

export type WidgetComponentType = typeof DashboardWidget & Type<DashboardWidget>;
