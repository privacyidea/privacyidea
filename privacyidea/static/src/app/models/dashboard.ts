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
import { computed, Directive, input, Signal, signal, TemplateRef, Type } from "@angular/core";
import { PolicyAction } from "@services/auth/policy-actions";

export const DASHBOARD_COLUMNS = 24;

export type WidgetState = "loading" | "ready" | "denied" | "error";

export type WidgetTypeId =
  | "news"
  | "tokens"
  | "token-types"
  | "authentication-activity"
  | "administration"
  | "policies"
  | "events"
  | "subscriptions"
  | "certificate-health"
  | "resolver-timing"
  | "notification-delivery"
  | "appearance"
  | "conditional-access";

export interface WidgetSize {
  cols: number;
  rows: number;
}

/**
 * The choices a widget lets its reader make and then keeps. They travel inside the layout document rather than in a
 * setting of their own, so one widget's settings are removed with the widget and restored with it, and so a dashboard
 * is saved in one request however many widgets were touched.
 */
export interface WidgetOptions {
  /**
   * The id of the time range or window the widget is read over, resolved against the widget's own list of presets.
   * One key rather than one per widget, because a widget that offers a span offers exactly one; an id it does not
   * know - a preset that was renamed, or another widget's vocabulary left behind by a widget swap - falls back to
   * that widget's default instead of showing nothing.
   */
  range?: string;
}

export interface WidgetInstance extends WidgetSize {
  id: string;
  type: WidgetTypeId;
  x: number;
  y: number;
  options?: WidgetOptions;
}

@Directive()
export abstract class DashboardWidget {
  readonly instance = input<WidgetInstance>();
  readonly state = signal<WidgetState>("loading");
  readonly loading = computed(() => this.state() === "loading");
  readonly partialLoading = computed(() => false);
  readonly refreshFailed = computed(() => false);
  readonly canReload = computed(() => true);
  readonly titleRoute = computed<string | null>(() => null);
  /**
   * Buttons the widget adds to its frame's header, in front of the reload button, so a
   * widget does not have to spend a row of its own body on a toolbar. A template rather
   * than a list of icons and callbacks, so a widget can hand over components that keep
   * state of their own — the copy button and its "copied" feedback, for one.
   */
  readonly headerActions?: Signal<TemplateRef<unknown> | undefined>;

  static readonly type: WidgetTypeId;
  static readonly title: string = "";
  static readonly icon: string = "";
  static readonly headerIcon: Type<unknown> | null = null;
  static readonly defaultSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly minSize: WidgetSize = { cols: 3, rows: 3 };
  static readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: Number.POSITIVE_INFINITY };
  static readonly pinned: boolean = false;
  static readonly fixedPosition: { x: number; y: number } | null = null;
  // The right(s) a widget needs to be offered at all; a list means any one is enough, for a widget summarizing several
  // separately-governed areas that then shows only the parts the admin may read.
  static readonly requiredAction: PolicyAction | PolicyAction[] | null = null;
  // Where the widget's title links to, for a widget that summarizes one page. Null leaves the title as plain text.
  static readonly titleLink: string | null = null;
  static readonly titleLinkAction: PolicyAction | null = null;

  abstract reload(): void;
}

export type WidgetComponentType = typeof DashboardWidget & Type<DashboardWidget>;
