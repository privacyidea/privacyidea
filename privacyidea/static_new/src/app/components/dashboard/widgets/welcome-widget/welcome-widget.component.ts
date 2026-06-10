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
import { Component } from "@angular/core";
import { DashboardWidget, WidgetSize } from "@models/dashboard";

@Component({
  selector: "app-welcome-widget",
  standalone: true,
  templateUrl: "./welcome-widget.component.html",
  styleUrls: ["../dashboard-widget.scss", "./welcome-widget.component.scss"]
})
export class WelcomeWidgetComponent extends DashboardWidget {
  static override readonly type = "welcome";
  static override readonly title = $localize`Welcome`;
  static override readonly icon = "waving_hand";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 4 };
  static override readonly minSize: WidgetSize = { cols: 5, rows: 3 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 6 };
}
