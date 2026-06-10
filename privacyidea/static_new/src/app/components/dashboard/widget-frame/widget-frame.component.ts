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
import { CdkDragHandle } from "@angular/cdk/drag-drop";
import { NgComponentOutlet } from "@angular/common";
import { Component, computed, inject, input } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { WidgetInstance } from "@models/dashboard";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService, WidgetRegistryServiceInterface } from "@services/dashboard/widget-registry.service";

@Component({
  selector: "app-widget-frame",
  standalone: true,
  imports: [NgComponentOutlet, MatIcon, MatIconButton, CdkDragHandle],
  templateUrl: "./widget-frame.component.html",
  styleUrl: "./widget-frame.component.scss"
})
export class WidgetFrameComponent {
  private readonly registry: WidgetRegistryServiceInterface = inject(WidgetRegistryService);
  protected readonly layoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);

  readonly instance = input.required<WidgetInstance>();

  protected readonly widgetType = computed(() => this.registry.get(this.instance().type));
  protected readonly component = computed(() => this.widgetType() ?? null);
  protected readonly outletInputs = computed(() => ({ instance: this.instance() }));

  protected remove(): void {
    this.layoutService.removeWidget(this.instance().id);
  }
}
