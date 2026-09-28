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
import { DASHBOARD_COLUMNS, WidgetInstance, WidgetOptions, WidgetSettings, WidgetTypeId } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
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

  isWidgetTypeAllowed(type: string): boolean;

  pruneForbiddenWidgets(): void;

  removeWidget(id: string): void;

  moveWidgetTo(id: string, x: number, y: number): void;

  resizeWidget(id: string, cols: number, rows: number): void;

  updateWidgetSettings(id: string, settings: WidgetSettings): void;

  setWidgetOptions(id: string, options: Partial<WidgetOptions>): void;

  persist(): void;

  resetLayout(): void;
}

@Injectable({
  providedIn: "root"
})
export class DashboardLayoutService implements DashboardLayoutServiceInterface {
  private readonly persistence: DashboardPersistenceServiceInterface = inject(DashboardPersistenceService);
  private readonly registry: WidgetRegistryServiceInterface = inject(WidgetRegistryService);
  private readonly auth: AuthServiceInterface = inject(AuthService);
  public readonly widgets: WritableSignal<WidgetInstance[]> = signal(this.reconcilePinned(this.defaultWidgets()));
  public readonly editMode = signal(false);
  public readonly insertRow: WritableSignal<number> = signal(0);

  constructor() {
    this.loadLayout();
  }

  public beginEdit(): void {
    this.snapshot = this.widgets().map((widget) => ({ ...widget }));
    this.editMode.set(true);
  }

  public saveEdit(): void {
    this.snapshot = null;
    this.editMode.set(false);
    this.persistIfLive();
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
    if (!this.isWidgetTypeAllowed(widgetType.type)) {
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

  public isWidgetTypeAllowed(type: string): boolean {
    const requiredAction = this.registry.get(type)?.requiredAction;
    // Length rather than truthiness, so an empty list reads as "no requirement" like null does.
    if (!requiredAction?.length) {
      return true;
    }
    // A widget may name several rights (see DashboardWidget.requiredAction); any one is enough, because the widget
    // renders only the parts the admin may read and leaves out the rest.
    const actions = Array.isArray(requiredAction) ? requiredAction : [requiredAction];
    return actions.some((action) => this.auth.actionAllowed(action));
  }

  public pruneForbiddenWidgets(): void {
    // Guard against wiping the stored layout while auth data is not yet available:
    // an empty rights list would otherwise mark every widget as forbidden.
    if (!this.auth.isAuthenticated()) {
      return;
    }
    const allowed = this.widgets().filter((widget) => this.isWidgetTypeAllowed(widget.type));
    if (allowed.length !== this.widgets().length) {
      this.widgets.set(allowed);
      this.persistIfLive();
    }
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

  public updateWidgetSettings(id: string, settings: WidgetSettings): void {
    this.widgets.update((widgets) =>
      widgets.map((widget) =>
        widget.id === id ? { ...widget, settings: { ...widget.settings, ...settings } } : widget
      )
    );
    this.persistIfLive();
  }

  /**
   * Merges *options* into what the widget already keeps, so a widget that later offers a second choice does not have
   * to resend the first. The pending snapshot is written through as well: the options are how the widget is read
   * rather than where it sits, and cancelling an arrangement should not also undo the window someone picked while
   * looking at it.
   */
  public setWidgetOptions(id: string, options: Partial<WidgetOptions>): void {
    const merge = (widget: WidgetInstance): WidgetInstance =>
      widget.id === id ? { ...widget, options: { ...widget.options, ...options } } : widget;
    this.widgets.update((widgets) => widgets.map(merge));
    if (this.snapshot) {
      this.snapshot = this.snapshot.map(merge);
    }
    this.persistIfLive();
  }

  public persist(): void {
    this.persistence.save(this.widgets()).subscribe();
  }

  public resetLayout(): void {
    this.widgets.set(this.allowedDefaultLayout());
    this.persistIfLive();
  }

  private snapshot: WidgetInstance[] | null = null;
  private loaded = false;
  private changedWhileLoading = false;

  private loadLayout(): void {
    this.persistence.load().subscribe((stored) => {
      this.loaded = true;
      // A layout the user changed while the request was in flight wins over the
      // stored one and is written back, so the change is not silently dropped.
      if (this.changedWhileLoading) {
        this.persist();
        return;
      }
      this.widgets.set(stored ? this.reconcilePinned(stored) : this.allowedDefaultLayout());
    });
  }

  private allowedDefaultLayout(): WidgetInstance[] {
    const current = new Map(this.widgets().map((widget) => [widget.type, widget]));
    const defaults = this.defaultWidgets()
      .filter((widget) => this.isWidgetTypeAllowed(widget.type))
      .map((widget) => {
        const existing = current.get(widget.type);
        return existing ? { ...widget, id: existing.id, options: existing.options } : widget;
      });
    return this.compactUpwards(this.reconcilePinned(defaults));
  }

  // Closes the gaps left by widgets the admin may not see without shuffling the columns around.
  private compactUpwards(widgets: WidgetInstance[]): WidgetInstance[] {
    const placed = widgets.filter((widget) => this.registry.get(widget.type)?.pinned);
    const movable = widgets
      .filter((widget) => !this.registry.get(widget.type)?.pinned)
      .sort((a, b) => a.y - b.y || a.x - b.x);
    for (const widget of movable) {
      let y = widget.y;
      while (y > 0 && !placed.some((other) => this.overlaps({ ...widget, y: y - 1 }, other))) {
        y--;
      }
      placed.push({ ...widget, y });
    }
    return placed;
  }

  private persistIfLive(): void {
    if (this.editMode()) {
      return;
    }
    // Writing the default layout before the stored one arrived would overwrite it.
    if (!this.loaded) {
      this.changedWhileLoading = true;
      return;
    }
    this.persist();
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
        other.rows === widget.rows &&
        this.sameSettings(other.settings, widget.settings)
      );
    });
  }

  private sameSettings(a: WidgetSettings | undefined, b: WidgetSettings | undefined): boolean {
    const keys = new Set([...Object.keys(a ?? {}), ...Object.keys(b ?? {})]);
    return [...keys].every((key) => a?.[key] === b?.[key]);
  }

  private reconcilePinned(widgets: WidgetInstance[]): WidgetInstance[] {
    const result: WidgetInstance[] = [];
    for (const widgetType of this.registry.widgetTypes) {
      if (!widgetType.pinned || !this.isWidgetTypeAllowed(widgetType.type)) {
        continue;
      }
      const existing = widgets.find((widget) => widget.type === widgetType.type);
      const { x, y } = widgetType.fixedPosition ?? { x: 0, y: 0 };
      const { cols, rows } = widgetType.defaultSize;
      result.push({
        id: existing?.id ?? `pinned-${widgetType.type}`,
        type: widgetType.type,
        x,
        y,
        cols,
        rows,
        ...(existing?.settings ? { settings: existing.settings } : {})
      });
    }
    for (const widget of widgets) {
      const widgetType = this.registry.get(widget.type);
      if (!widgetType || widgetType.pinned) {
        continue;
      }
      if (!result.some((other) => this.overlaps(widget, other))) {
        result.push(widget);
      }
    }
    return result;
  }

  private findFreeSpot(cols: number, rows: number): { x: number; y: number } {
    const widgets = this.widgets();
    const maxX = Math.max(0, DASHBOARD_COLUMNS - cols);
    for (let y = Math.max(0, this.insertRow()); ; y++) {
      for (let x = 0; x <= maxX; x++) {
        if (!widgets.some((other) => this.overlaps({ x, y, cols, rows }, other))) {
          return { x, y };
        }
      }
    }
  }

  private overlaps(
    a: Pick<WidgetInstance, "x" | "y" | "cols" | "rows">,
    b: Pick<WidgetInstance, "x" | "y" | "cols" | "rows">
  ): boolean {
    return a.x < b.x + b.cols && a.x + a.cols > b.x && a.y < b.y + b.rows && a.y + a.rows > b.y;
  }

  private defaultWidgets(): WidgetInstance[] {
    const positions: { type: WidgetTypeId; x: number; y: number; cols?: number; rows?: number }[] = [
      { type: "authentication-activity", x: 0, y: 0 },
      { type: "tokens", x: 6, y: 0, rows: 4 },
      { type: "token-types", x: 12, y: 0, cols: 4, rows: 4 },
      { type: "certificate-health", x: 6, y: 4, cols: 10, rows: 4 },
      { type: "resolver-timing", x: 0, y: 8, cols: 16 },
      { type: "notification-delivery", x: 16, y: 11 },
      { type: "conditional-access", x: 0, y: 14 },
      { type: "policies", x: 7, y: 14, cols: 9, rows: 8 }
    ];
    return positions.reduce<WidgetInstance[]>((result, { type, x, y, cols, rows }) => {
      const widgetType = this.registry.get(type);
      if (widgetType) {
        result.push({
          id: uuid(),
          type,
          x,
          y,
          cols: cols ?? widgetType.defaultSize.cols,
          rows: rows ?? widgetType.defaultSize.rows
        });
      }
      return result;
    }, []);
  }
}
