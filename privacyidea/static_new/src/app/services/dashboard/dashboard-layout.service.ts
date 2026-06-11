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
import { inject, Injectable, signal, WritableSignal } from "@angular/core";
import { DASHBOARD_COLUMNS, WidgetInstance } from "@models/dashboard";
import {
  DashboardPersistenceService,
  DashboardPersistenceServiceInterface
} from "@services/dashboard/dashboard-persistence.service";
import { WidgetRegistryService, WidgetRegistryServiceInterface } from "@services/dashboard/widget-registry.service";
import { v4 as uuid } from "uuid";

export interface DashboardLayoutServiceInterface {
  readonly widgets: WritableSignal<WidgetInstance[]>;
  readonly editMode: WritableSignal<boolean>;
  readonly insertRow: WritableSignal<number>;

  beginEdit(): void;

  saveEdit(): void;

  cancelEdit(): void;

  hasPendingChanges(): boolean;

  addWidget(type: string): void;

  hasWidgetOfType(type: string): boolean;

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
  public readonly widgets: WritableSignal<WidgetInstance[]> = signal(
    this.reconcilePinned(this.persistence.load() ?? this.defaultWidgets())
  );

  public readonly insertRow: WritableSignal<number> = signal(0);

  private snapshot: WidgetInstance[] | null = null;

  public beginEdit(): void {
    this.snapshot = this.widgets().map((widget) => ({ ...widget }));
    this.editMode.set(true);
  }

  public saveEdit(): void {
    this.snapshot = null;
    this.editMode.set(false);
    this.persist();
  }

  public cancelEdit(): void {
    if (this.snapshot) {
      this.widgets.set(this.snapshot);
      this.snapshot = null;
    }
    this.editMode.set(false);
  }

  public hasPendingChanges(): boolean {
    return this.snapshot !== null && !this.sameLayout(this.widgets(), this.snapshot);
  }

  public addWidget(type: string): void {
    const widgetType = this.registry.get(type);
    if (!widgetType) {
      return;
    }
    if (this.hasWidgetOfType(widgetType.type)) {
      return;
    }
    const { cols, rows } = widgetType.defaultSize;
    const { x, y } = this.findFreeSpot(cols, rows);
    const widget: WidgetInstance = { id: uuid(), type: widgetType.type, x, y, cols, rows };
    this.widgets.update((widgets) => [...widgets, widget]);
    this.persistIfLive();
  }

  public hasWidgetOfType(type: string): boolean {
    return this.widgets().some((widget) => widget.type === type);
  }

  public removeWidget(id: string): void {
    const widget = this.widgets().find((candidate) => candidate.id === id);
    if (widget && this.registry.get(widget.type)?.pinned) {
      return;
    }
    this.widgets.update((widgets) => widgets.filter((widget) => widget.id !== id));
    this.persistIfLive();
  }

  public moveWidgetTo(id: string, x: number, y: number): void {
    this.widgets.update((widgets) => widgets.map((widget) => (widget.id === id ? { ...widget, x, y } : widget)));
    this.persistIfLive();
  }

  public resizeWidget(id: string, cols: number, rows: number): void {
    this.widgets.update((widgets) => widgets.map((widget) => (widget.id === id ? { ...widget, cols, rows } : widget)));
    this.persistIfLive();
  }

  public persist(): void {
    this.persistence.save(this.widgets());
  }

  public resetLayout(): void {
    this.widgets.set(this.reconcilePinned(this.defaultWidgets()));
    this.persistIfLive();
  }

  private persistIfLive(): void {
    if (!this.editMode()) {
      this.persist();
    }
  }

  private sameLayout(a: WidgetInstance[], b: WidgetInstance[]): boolean {
    if (a.length !== b.length) {
      return false;
    }
    const byId = new Map(b.map((widget) => [widget.id, widget]));
    return a.every((widget) => {
      const other = byId.get(widget.id);
      return (
        !!other &&
        other.type === widget.type &&
        other.x === widget.x &&
        other.y === widget.y &&
        other.cols === widget.cols &&
        other.rows === widget.rows
      );
    });
  }

  private reconcilePinned(widgets: WidgetInstance[]): WidgetInstance[] {
    const result = widgets.filter((widget) => !this.registry.get(widget.type)?.pinned);
    for (const widgetType of this.registry.widgetTypes) {
      if (!widgetType.pinned) {
        continue;
      }
      const { x, y } = widgetType.fixedPosition ?? { x: 0, y: 0 };
      const { cols, rows } = widgetType.defaultSize;
      result.push({ id: uuid(), type: widgetType.type, x, y, cols, rows });
    }
    return result;
  }

  private findFreeSpot(cols: number, rows: number): { x: number; y: number } {
    const widgets = this.widgets();
    const maxX = Math.max(0, DASHBOARD_COLUMNS - cols);
    for (let y = Math.max(0, this.insertRow()); ; y++) {
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

  private defaultWidgets(): WidgetInstance[] {
    const positions: { type: string; x: number; y: number }[] = [
      { type: "tokens", x: 0, y: 0 },
      { type: "events", x: 0, y: 8 },
      { type: "policies", x: 6, y: 0 },
      { type: "administration", x: 6, y: 5 },
      { type: "authentications", x: 16, y: 5 }
    ];
    return positions.reduce<WidgetInstance[]>((result, { type, x, y }) => {
      const widgetType = this.registry.get(type);
      if (widgetType) {
        result.push({ id: uuid(), type, x, y, ...widgetType.defaultSize });
      }
      return result;
    }, []);
  }
}
