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
import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { DASHBOARD_COLUMNS, DashboardLayout, WidgetInstance } from "@models/dashboard";
import {
  DashboardPersistenceService,
  DashboardPersistenceServiceInterface
} from "@services/dashboard/dashboard-persistence.service";
import { WidgetRegistryService, WidgetRegistryServiceInterface } from "@services/dashboard/widget-registry.service";
import { v4 as uuid } from "uuid";

export interface DashboardLayoutServiceInterface {
  readonly layout: WritableSignal<DashboardLayout>;
  readonly widgets: Signal<WidgetInstance[]>;
  readonly editMode: WritableSignal<boolean>;

  toggleEditMode(): void;

  addWidget(type: string): void;

  removeWidget(id: string): void;

  moveWidgetTo(id: string, x: number, y: number): void;

  resizeWidget(id: string, cols: number, rows: number): void;

  persist(): void;

  resetLayout(): void;
}

@Injectable({
  providedIn: "root"
})
export class DashboardLayoutService implements DashboardLayoutServiceInterface {
  private readonly persistence: DashboardPersistenceServiceInterface = inject(DashboardPersistenceService);
  private readonly registry: WidgetRegistryServiceInterface = inject(WidgetRegistryService);

  public readonly editMode = signal(false);
  public readonly layout: WritableSignal<DashboardLayout> = signal(this.persistence.load() ?? this.defaultLayout());
  public readonly widgets = computed(() => this.layout().widgets);

  public toggleEditMode(): void {
    this.editMode.update((value) => !value);
  }

  public addWidget(type: string): void {
    const definition = this.registry.get(type);
    if (!definition) {
      return;
    }
    const { cols, rows } = definition.defaultSize;
    const { x, y } = this.findFreeSpot(cols, rows);
    const widget: WidgetInstance = { id: uuid(), type, x, y, cols, rows };
    this.layout.update((layout) => ({ ...layout, widgets: [...layout.widgets, widget] }));
    this.persist();
  }

  public removeWidget(id: string): void {
    this.layout.update((layout) => ({
      ...layout,
      widgets: layout.widgets.filter((widget) => widget.id !== id)
    }));
    this.persist();
  }

  public moveWidgetTo(id: string, x: number, y: number): void {
    this.layout.update((layout) => ({
      ...layout,
      widgets: layout.widgets.map((widget) => (widget.id === id ? { ...widget, x, y } : widget))
    }));
    this.persist();
  }

  public resizeWidget(id: string, cols: number, rows: number): void {
    this.layout.update((layout) => ({
      ...layout,
      widgets: layout.widgets.map((widget) => (widget.id === id ? { ...widget, cols, rows } : widget))
    }));
    this.persist();
  }

  public persist(): void {
    this.persistence.save(this.layout());
  }

  public resetLayout(): void {
    this.layout.set(this.defaultLayout());
    this.persist();
  }

  private findFreeSpot(cols: number, rows: number): { x: number; y: number } {
    const widgets = this.layout().widgets;
    const maxX = Math.max(0, DASHBOARD_COLUMNS - cols);
    for (let y = 0; ; y++) {
      for (let x = 0; x <= maxX; x++) {
        const overlaps = widgets.some(
          (other) => x < other.x + other.cols && x + cols > other.x && y < other.y + other.rows && y + rows > other.y
        );
        if (!overlaps) {
          return { x, y };
        }
      }
    }
  }

  private defaultLayout(): DashboardLayout {
    return {
      id: "default",
      widgets: [{ id: uuid(), type: "welcome", x: 0, y: 0, cols: 8, rows: 4 }]
    };
  }
}
