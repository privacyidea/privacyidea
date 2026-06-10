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
import { Component, inject } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { WidgetComponentType } from "@models/dashboard";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService, WidgetRegistryServiceInterface } from "@services/dashboard/widget-registry.service";

@Component({
  selector: "app-widget-palette",
  standalone: true,
  imports: [MatButton, MatIcon],
  templateUrl: "./widget-palette.component.html",
  styleUrl: "./widget-palette.component.scss"
})
export class WidgetPaletteComponent {
  private readonly registry: WidgetRegistryServiceInterface = inject(WidgetRegistryService);
  private readonly layoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);

  protected readonly widgetTypes: WidgetComponentType[] = this.registry.widgetTypes;

  protected add(type: string): void {
    this.layoutService.addWidget(type);
  }
}
