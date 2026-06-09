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
import { Component, computed, input } from "@angular/core";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";

@Component({
  selector: "app-stat-widget",
  standalone: true,
  template: `
    <div class="stat-value">{{ value() }}</div>
    <div class="stat-caption">{{ caption() }}</div>
  `,
  styles: [
    `
      :host {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
      }

      .stat-value {
        font-size: 2.5rem;
        font-weight: 600;
        line-height: 1;
      }

      .stat-caption {
        opacity: 0.7;
      }
    `
  ]
})
export class StatWidgetComponent implements DashboardWidget {
  readonly instance = input<WidgetInstance>();

  readonly value = computed(() => (this.instance()?.config?.["value"] as string | number) ?? "—");
  readonly caption = computed(() => (this.instance()?.config?.["caption"] as string) ?? "");
}
