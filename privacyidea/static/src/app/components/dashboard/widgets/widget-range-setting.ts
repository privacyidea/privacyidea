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
import { inject, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { WidgetInstance } from "@models/dashboard";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";

/**
 * The span a widget is read over, kept where it outlives a reload: in the widget's own entry of the stored dashboard
 * layout, rather than in a signal that starts again at the default every time the page is opened.
 *
 * Constructed in a widget's field initializer, which is what puts it in an injection context::
 *
 *     protected readonly window = new WidgetRangeSetting(this.instance, METRICS_WINDOWS, DEFAULT_METRICS_WINDOW);
 *
 * The selection follows the stored id rather than standing beside it, so a layout arriving after the widget has been
 * drawn - the settings request is in flight while the dashboard renders its defaults - moves the widget onto the
 * stored window instead of leaving the two disagreeing.
 */
export class WidgetRangeSetting<T extends { id: string }> {
  private readonly layoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);

  readonly selected: WritableSignal<T>;

  constructor(
    private readonly instance: Signal<WidgetInstance | undefined>,
    private readonly choices: readonly T[],
    private readonly fallback: T
  ) {
    this.selected = linkedSignal<string | undefined, T>({
      source: () => this.instance()?.options?.range,
      // An id this widget does not know keeps what is on screen rather than snapping to the default: it is a window a
      // newer WebUI offers, or one left behind by a widget that was removed and its slot reused.
      computation: (stored, previous) => this.byId(stored) ?? previous?.value ?? this.fallback
    });
  }

  select(id: string): void {
    const choice = this.byId(id);
    if (!choice) {
      return;
    }
    // Set here as well as written through: a principal whose settings are not stored - role "user", whose document
    // the backend does not keep - still gets the window they picked for as long as the dashboard is open.
    this.selected.set(choice);
    const widgetId = this.instance()?.id;
    if (widgetId) {
      this.layoutService.setWidgetOptions(widgetId, { range: id });
    }
  }

  private byId(id: string | undefined): T | undefined {
    return id === undefined ? undefined : this.choices.find((choice) => choice.id === id);
  }
}
