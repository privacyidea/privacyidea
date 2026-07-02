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
import { Component, computed, inject, input, viewChild } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatProgressSpinner } from "@angular/material/progress-spinner";
import { WidgetInstance, WidgetState } from "@models/dashboard";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService, WidgetRegistryServiceInterface } from "@services/dashboard/widget-registry.service";

interface DashboardWidgetLike {
  state?: () => WidgetState;
  loading?: () => boolean;
  partialLoading?: () => boolean;
  reload?: () => void;
}

@Component({
  selector: "app-widget-frame",
  standalone: true,
  imports: [NgComponentOutlet, MatIcon, MatIconButton, MatProgressSpinner, CdkDragHandle],
  templateUrl: "./widget-frame.component.html",
  styleUrl: "./widget-frame.component.scss"
})
export class WidgetFrameComponent {
  private readonly registry: WidgetRegistryServiceInterface = inject(WidgetRegistryService);
  protected readonly layoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);

  readonly instance = input.required<WidgetInstance>();

  private readonly outlet = viewChild(NgComponentOutlet);

  protected readonly widgetType = computed(() => this.registry.get(this.instance().type));
  protected readonly component = computed(() => this.widgetType() ?? null);
  protected readonly pinned = computed(() => this.widgetType()?.pinned ?? false);
  protected readonly outletInputs = computed(() => ({ instance: this.instance() }));

  protected readonly initialLoading = computed(() => {
    const instance = this.outlet()?.componentInstance as DashboardWidgetLike | undefined;
    return instance?.state?.() === "loading";
  });

  protected readonly loading = computed(() => {
    const instance = this.outlet()?.componentInstance as DashboardWidgetLike | undefined;
    return instance?.loading?.() ?? false;
  });

  protected readonly partialLoading = computed(() => {
    const instance = this.outlet()?.componentInstance as DashboardWidgetLike | undefined;
    return instance?.partialLoading?.() ?? false;
  });

  protected readonly showHeaderSpinner = computed(
    () => !this.initialLoading() && (this.loading() || this.partialLoading())
  );
  protected readonly showReload = computed(() => !this.initialLoading() && !this.showHeaderSpinner());

  protected reload(): void {
    const instance = this.outlet()?.componentInstance as DashboardWidgetLike | undefined;
    instance?.reload?.();
  }

  protected remove(): void {
    this.layoutService.removeWidget(this.instance().id);
  }
}
