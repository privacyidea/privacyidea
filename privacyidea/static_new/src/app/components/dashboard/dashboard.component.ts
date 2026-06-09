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
import { CdkDrag, CdkDragEnd, CdkDragMove, CdkDragStart } from "@angular/cdk/drag-drop";
import { Component, computed, ElementRef, inject, signal, viewChild } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { WidgetFrameComponent } from "@components/dashboard/widget-frame/widget-frame.component";
import { WidgetPaletteComponent } from "@components/dashboard/widget-palette/widget-palette.component";
import { DASHBOARD_COLUMNS, WidgetInstance } from "@models/dashboard";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService, WidgetRegistryServiceInterface } from "@services/dashboard/widget-registry.service";

interface FieldRect {
  x: number;
  y: number;
  cols: number;
  rows: number;
}

type ResizeDir = "e" | "s" | "se";

interface ResizeState {
  id: string;
  dir: ResizeDir;
  startX: number;
  startY: number;
  startCols: number;
  startRows: number;
  minCols: number;
  minRows: number;
  maxCols: number;
  rect: FieldRect;
  pitchX: number;
  pitchY: number;
}

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CdkDrag, WidgetFrameComponent, WidgetPaletteComponent, MatButton, MatIcon],
  templateUrl: "./dashboard.component.html",
  styleUrl: "./dashboard.component.scss"
})
export class DashboardComponent {
  protected readonly layoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);
  private readonly registry: WidgetRegistryServiceInterface = inject(WidgetRegistryService);
  protected readonly widgets = this.layoutService.widgets;

  private resizeState: ResizeState | null = null;
  protected readonly resizePreview = signal<{ id: string; cols: number; rows: number; valid: boolean } | null>(null);

  protected readonly columns = DASHBOARD_COLUMNS;
  protected readonly rowHeight = 40;
  protected readonly gap = 4;

  private readonly field = viewChild.required<ElementRef<HTMLElement>>("field");
  private readonly fieldScroll = viewChild.required<ElementRef<HTMLElement>>("fieldScroll");
  private dragState: { id: string; widget: WidgetInstance; element: HTMLElement; startScrollTop: number } | null = null;

  protected readonly dragTarget = signal<(FieldRect & { valid: boolean }) | null>(null);

  protected readonly rowCount = computed(() => {
    const maxBottom = this.widgets().reduce((bottom, widget) => Math.max(bottom, widget.y + widget.rows), 0);
    return maxBottom + 4;
  });

  protected readonly fieldHeight = computed(() => this.heightPx(this.rowCount()));

  protected anchorBackgroundSize(): string {
    return `calc((100% + ${this.gap}px) / ${this.columns}) ${this.rowHeight + this.gap}px`;
  }

  protected leftCss(x: number): string {
    return `calc(${x} * ((100% - ${(this.columns - 1) * this.gap}px) / ${this.columns} + ${this.gap}px))`;
  }

  protected widthCss(cols: number): string {
    return `calc(${cols} * (100% - ${(this.columns - 1) * this.gap}px) / ${this.columns} + ${(cols - 1) * this.gap}px)`;
  }

  protected topPx(y: number): number {
    return y * (this.rowHeight + this.gap);
  }

  protected heightPx(rows: number): number {
    return rows * this.rowHeight + (rows - 1) * this.gap;
  }

  protected onDragStarted(widget: WidgetInstance, event: CdkDragStart): void {
    this.dragState = {
      id: widget.id,
      widget,
      element: event.source.element.nativeElement,
      startScrollTop: this.fieldScroll().nativeElement.scrollTop
    };
  }

  protected onFieldScroll(): void {
    const state = this.dragState;
    if (!state) {
      return;
    }
    const delta = this.fieldScroll().nativeElement.scrollTop - state.startScrollTop;
    state.element.style.translate = `0 ${delta}px`;
    const target = this.targetRect(state.widget, state.element);
    this.dragTarget.set({ ...target, valid: !this.collides(target, state.id) });
  }

  protected onDragMoved(widget: WidgetInstance, event: CdkDragMove): void {
    const target = this.targetRect(widget, event.source.element.nativeElement);
    this.dragTarget.set({ ...target, valid: !this.collides(target, widget.id) });
  }

  protected onDragEnded(widget: WidgetInstance, event: CdkDragEnd): void {
    const target = this.targetRect(widget, event.source.element.nativeElement);
    this.dragTarget.set(null);
    if (this.dragState) {
      this.dragState.element.style.translate = "";
      this.dragState = null;
    }
    event.source.reset();
    if (!this.collides(target, widget.id)) {
      this.layoutService.moveWidgetTo(widget.id, target.x, target.y);
    }
  }

  private targetRect(widget: WidgetInstance, element: HTMLElement): FieldRect {
    const fieldRect = this.field().nativeElement.getBoundingClientRect();
    const rect = element.getBoundingClientRect();
    const pitchX = (fieldRect.width + this.gap) / this.columns;
    const pitchY = this.rowHeight + this.gap;
    const x = Math.min(Math.max(Math.round((rect.left - fieldRect.left) / pitchX), 0), this.columns - widget.cols);
    const y = Math.max(Math.round((rect.top - fieldRect.top) / pitchY), 0);
    return { x, y, cols: widget.cols, rows: widget.rows };
  }

  protected onResizeStart(widget: WidgetInstance, dir: ResizeDir, event: PointerEvent): void {
    event.preventDefault();
    event.stopPropagation();
    (event.target as HTMLElement).setPointerCapture(event.pointerId);

    const fieldRect = this.field().nativeElement.getBoundingClientRect();
    const definition = this.registry.get(widget.type);
    this.resizeState = {
      id: widget.id,
      dir,
      startX: event.clientX,
      startY: event.clientY,
      startCols: widget.cols,
      startRows: widget.rows,
      minCols: definition?.minSize?.cols ?? 1,
      minRows: definition?.minSize?.rows ?? 1,
      maxCols: Math.min(definition?.maxSize?.cols ?? this.columns, this.columns - widget.x),
      rect: { x: widget.x, y: widget.y, cols: widget.cols, rows: widget.rows },
      pitchX: (fieldRect.width + this.gap) / this.columns,
      pitchY: this.rowHeight + this.gap
    };
  }

  protected onResizeMove(event: PointerEvent): void {
    const state = this.resizeState;
    if (!state) {
      return;
    }
    let cols = state.startCols;
    let rows = state.startRows;
    if (state.dir !== "s") {
      const deltaCols = Math.round((event.clientX - state.startX) / state.pitchX);
      cols = Math.min(Math.max(state.startCols + deltaCols, state.minCols), state.maxCols);
    }
    if (state.dir !== "e") {
      const deltaRows = Math.round((event.clientY - state.startY) / state.pitchY);
      rows = Math.max(state.startRows + deltaRows, state.minRows);
    }
    const target: FieldRect = { x: state.rect.x, y: state.rect.y, cols, rows };
    this.resizePreview.set({ id: state.id, cols, rows, valid: !this.collides(target, state.id) });
  }

  protected onResizeEnd(): void {
    const preview = this.resizePreview();
    this.resizeState = null;
    this.resizePreview.set(null);
    if (preview?.valid) {
      this.layoutService.resizeWidget(preview.id, preview.cols, preview.rows);
    }
  }

  protected effectiveCols(widget: WidgetInstance): number {
    const preview = this.resizePreview();
    return preview?.id === widget.id ? preview.cols : widget.cols;
  }

  protected effectiveRows(widget: WidgetInstance): number {
    const preview = this.resizePreview();
    return preview?.id === widget.id ? preview.rows : widget.rows;
  }

  protected isResizingInvalid(widget: WidgetInstance): boolean {
    const preview = this.resizePreview();
    return preview?.id === widget.id && !preview.valid;
  }

  private collides(rect: FieldRect, excludeId: string): boolean {
    return this.widgets().some(
      (other) =>
        other.id !== excludeId &&
        rect.x < other.x + other.cols &&
        rect.x + rect.cols > other.x &&
        rect.y < other.y + other.rows &&
        rect.y + rect.rows > other.y
    );
  }

  protected toggleEdit(): void {
    this.layoutService.toggleEditMode();
  }

  protected reset(): void {
    this.layoutService.resetLayout();
  }
}
