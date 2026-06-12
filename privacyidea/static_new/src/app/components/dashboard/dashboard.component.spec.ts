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
import { CdkDragEnd, CdkDragMove, CdkDragStart } from "@angular/cdk/drag-drop";
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SubscriptionService } from "@services/subscription/subscription.service";
import { TokenService } from "@services/token/token.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { DashboardComponent } from "./dashboard.component";

describe("DashboardComponent", () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let layoutService: DashboardLayoutService;

  const FIELD_WIDTH = 1196;

  const stubFieldRect = (): void => {
    const field = component['field']().nativeElement as HTMLElement;
    field.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: FIELD_WIDTH, height: 1000, right: FIELD_WIDTH, bottom: 1000, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
  };

  const stubScroll = (scrollTop: number, clientHeight: number, scrollHeight: number): HTMLElement => {
    const el = component['fieldScroll']().nativeElement as HTMLElement;
    Object.defineProperty(el, "clientHeight", { value: clientHeight, configurable: true });
    Object.defineProperty(el, "scrollHeight", { value: scrollHeight, configurable: true });
    el.scrollTop = scrollTop;
    return el;
  };

  const pointerEvent = (overrides: Partial<PointerEvent> = {}): PointerEvent =>
    ({
      clientX: 0,
      clientY: 0,
      pointerId: 1,
      preventDefault: jest.fn(),
      stopPropagation: jest.fn(),
      target: { setPointerCapture: jest.fn() },
      ...overrides
    }) as unknown as PointerEvent;

  const dragEvent = (element: HTMLElement) => ({
    source: { element: { nativeElement: element }, reset: jest.fn() }
  });

  const firstWidget = (): WidgetInstance => layoutService.widgets()[0];

  const pinnedWidget = (): WidgetInstance => layoutService.widgets().find((widget) => widget.type === "subscriptions")!;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        PendingChangesService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SubscriptionService, useClass: MockSubscriptionService }
      ]
    }).compileComponents();

    layoutService = TestBed.inject(DashboardLayoutService);
    layoutService.widgets.set([
      { id: "tokens-1", type: "tokens", x: 0, y: 0, cols: 6, rows: 8 },
      { id: "subscriptions-1", type: "subscriptions", x: 16, y: 0, cols: 8, rows: 5 }
    ]);
    layoutService.editMode.set(false);

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("layout geometry helpers", () => {
    it("should build the left offset for a column index", () => {
      expect(component['leftCss'](2)).toBe("calc(2 * ((100% - 92px) / 24 + 4px))");
    });

    it("should build the width for a column span", () => {
      expect(component['widthCss'](3)).toBe("calc(3 * (100% - 92px) / 24 + 8px)");
    });

    it("should compute the top offset from the row pitch", () => {
      expect(component['topPx'](3)).toBe(132);
    });

    it("should compute the height for a row span", () => {
      expect(component['heightPx'](2)).toBe(84);
    });

    it("should expose the dot-grid background size", () => {
      expect(component['anchorBackgroundSize']()).toBe("calc((100% + 4px) / 24) 44px");
    });
  });

  describe("rowCount / fieldHeight", () => {
    it("should be exactly the lowest widget's bottom in view mode", () => {
      expect(component['rowCount']()).toBe(8);
      expect(component['fieldHeight']()).toBe(component['heightPx'](8));
    });

    it("should add trailing rows in edit mode", () => {
      layoutService.editMode.set(true);
      component['viewportBottom'].set(0);
      expect(component['rowCount']()).toBe(12);
    });

    it("should extend past the visible viewport while editing", () => {
      layoutService.editMode.set(true);
      component['viewportBottom'].set(440);
      expect(component['rowCount']()).toBe(14);
    });
  });

  describe("scroll metrics", () => {
    it("should flag the bottom when scrolled to the end", () => {
      stubScroll(600, 400, 1000);
      component['onFieldScroll']();
      expect(component['atBottom']()).toBe(true);
    });

    it("should not flag the bottom when more content is below", () => {
      stubScroll(0, 400, 1000);
      component['onFieldScroll']();
      expect(component['atBottom']()).toBe(false);
    });

    it("should track the top visible row as the preferred insert row", () => {
      stubScroll(440, 400, 2000);
      component['onFieldScroll']();
      expect(layoutService.insertRow()).toBe(10);
    });
  });

  describe("collision detection", () => {
    it("should report a collision with an overlapping widget", () => {
      expect(component['collides']({ x: 0, y: 0, cols: 1, rows: 1 }, "other")).toBe(true);
    });

    it("should exclude the widget being moved", () => {
      expect(component['collides']({ x: 0, y: 0, cols: 1, rows: 1 }, firstWidget().id)).toBe(false);
    });

    it("should report no collision in an empty area", () => {
      expect(component['collides']({ x: 20, y: 20, cols: 2, rows: 2 }, "other")).toBe(false);
    });
  });

  describe("resize preview accessors", () => {
    it("should use the preview size for the widget being resized", () => {
      const widget = firstWidget();
      component['resizePreview'].set({ id: widget.id, cols: 10, rows: 6, valid: true });

      expect(component['effectiveCols'](widget)).toBe(10);
      expect(component['effectiveRows'](widget)).toBe(6);
    });

    it("should keep the original size for other widgets", () => {
      const widget = firstWidget();
      component['resizePreview'].set({ id: "someone-else", cols: 10, rows: 6, valid: true });

      expect(component['effectiveCols'](widget)).toBe(widget.cols);
      expect(component['effectiveRows'](widget)).toBe(widget.rows);
    });

    it("should clamp an oversized stored widget down to its max for display", () => {
      const oversized: WidgetInstance = { id: "x", type: "tokens", x: 0, y: 0, cols: 20, rows: 20 };
      expect(component['effectiveCols'](oversized)).toBe(12);
      expect(component['effectiveRows'](oversized)).toBe(9);
    });

    it("should clamp an undersized stored widget up to its min for display", () => {
      const tiny: WidgetInstance = { id: "x", type: "tokens", x: 0, y: 0, cols: 1, rows: 1 };
      expect(component['effectiveCols'](tiny)).toBe(4);
      expect(component['effectiveRows'](tiny)).toBe(5);
    });

    it("should clamp display width to the field's right edge", () => {
      const nearEdge: WidgetInstance = { id: "x", type: "tokens", x: 22, y: 0, cols: 8, rows: 8 };
      expect(component['effectiveCols'](nearEdge)).toBe(2);
    });

    it("should report an invalid resize only for the previewed widget", () => {
      const widget = firstWidget();
      component['resizePreview'].set({ id: widget.id, cols: 10, rows: 6, valid: false });

      expect(component['isResizingInvalid'](widget)).toBe(true);
      expect(component['isResizingInvalid']({ ...widget, id: "other" })).toBe(false);
    });
  });

  describe("resize interaction", () => {
    beforeEach(() => {
      stubFieldRect();
      layoutService.editMode.set(true);
    });

    it("should clamp the width down to the effective minimum (tokens: 4 cols)", () => {
      const widget = firstWidget();
      component['onResizeStart'](widget, "e", pointerEvent({ clientX: 1000 }));
      component['onResizeMove'](pointerEvent({ clientX: 0 }));

      expect(component['resizePreview']()?.cols).toBe(4);
    });

    it("should clamp the width up to the widget's max (tokens: 12 cols)", () => {
      const widget = firstWidget();
      component['onResizeStart'](widget, "e", pointerEvent({ clientX: 0 }));
      component['onResizeMove'](pointerEvent({ clientX: 100000 }));

      expect(component['resizePreview']()?.cols).toBe(12);
    });

    it("should clamp the height down to the effective minimum (tokens: 5 rows)", () => {
      const widget = firstWidget();
      component['onResizeStart'](widget, "s", pointerEvent({ clientY: 1000 }));
      component['onResizeMove'](pointerEvent({ clientY: 0 }));

      expect(component['resizePreview']()?.rows).toBe(5);
    });

    it("should clamp the height up to the widget's max (tokens: 9 rows)", () => {
      const widget = firstWidget();
      component['onResizeStart'](widget, "s", pointerEvent({ clientY: 0 }));
      component['onResizeMove'](pointerEvent({ clientY: 100000 }));

      expect(component['resizePreview']()?.rows).toBe(9);
    });

    it("should apply a valid resize to the layout on resize end", () => {
      const resizeSpy = jest.spyOn(layoutService, "resizeWidget");
      const widget = firstWidget();

      component['onResizeStart'](widget, "se", pointerEvent({ clientX: 0, clientY: 0 }));
      component['onResizeMove'](pointerEvent({ clientX: 100, clientY: 88 }));
      component['onResizeEnd']();

      expect(resizeSpy).toHaveBeenCalledWith(widget.id, 8, 9);
      expect(component['resizePreview']()).toBeNull();
    });

    it("should not apply an invalid resize", () => {
      const resizeSpy = jest.spyOn(layoutService, "resizeWidget");
      component['resizePreview'].set({ id: firstWidget().id, cols: 10, rows: 6, valid: false });

      component['onResizeEnd']();

      expect(resizeSpy).not.toHaveBeenCalled();
    });

    it("should pin a pinned widget to its fixed size while resizing", () => {
      const pinned = pinnedWidget();

      component['onResizeStart'](pinned, "se", pointerEvent({ clientX: 0, clientY: 0 }));
      component['onResizeMove'](pointerEvent({ clientX: 100000, clientY: 100000 }));

      const preview = component['resizePreview']();
      expect(preview?.cols).toBe(8);
      expect(preview?.rows).toBe(5);
    });

    it("should ignore a resize move without an active resize", () => {
      component['onResizeMove'](pointerEvent({ clientX: 100, clientY: 100 }));
      expect(component['resizePreview']()).toBeNull();
    });
  });

  describe("pinned widgets", () => {
    it("should report the pinned widget as pinned", () => {
      expect(component['isPinned'](pinnedWidget())).toBe(true);
    });

    it("should report a regular widget as not pinned", () => {
      expect(component['isPinned'](firstWidget())).toBe(false);
    });
  });

  describe("drag interaction", () => {
    beforeEach(() => {
      stubFieldRect();
      layoutService.editMode.set(true);
    });

    it("should remember the widget being dragged on drag start", () => {
      const widget = firstWidget();
      const element = document.createElement("div");
      component['onDragStarted'](widget, dragEvent(element) as unknown as CdkDragStart);

      expect(component['dragState']?.id).toBe(widget.id);
    });

    it("should publish a drop target while dragging", () => {
      const widget = firstWidget();
      const element = document.createElement("div");
      component['onDragMoved'](widget, dragEvent(element) as unknown as CdkDragMove);

      const target = component['dragTarget']();
      expect(target).not.toBeNull();
      expect(target?.x).toBe(0);
      expect(target?.valid).toBe(true);
    });

    it("should move the widget and clear the drop target on drag end", () => {
      const moveSpy = jest.spyOn(layoutService, "moveWidgetTo");
      const widget = firstWidget();
      const element = document.createElement("div");

      component['onDragStarted'](widget, dragEvent(element) as unknown as CdkDragStart);
      component['onDragEnded'](widget, dragEvent(element) as unknown as CdkDragEnd);

      expect(moveSpy).toHaveBeenCalledWith(widget.id, 0, 0);
      expect(component['dragTarget']()).toBeNull();
      expect(component['dragState']).toBeNull();
    });

    it("should not move the widget when the drop target collides", () => {
      const moveSpy = jest.spyOn(layoutService, "moveWidgetTo");
      const widget = firstWidget();
      const element = document.createElement("div");
      element.getBoundingClientRect = () =>
        ({ left: 800, top: 0, width: 0, height: 0, right: 800, bottom: 0, x: 800, y: 0, toJSON: () => ({}) }) as DOMRect;

      component['onDragEnded'](widget, dragEvent(element) as unknown as CdkDragEnd);

      expect(moveSpy).not.toHaveBeenCalled();
      expect(component['dragTarget']()).toBeNull();
    });

    it("should follow the scroll position and update the drop target while dragging", () => {
      const widget = firstWidget();
      const element = document.createElement("div");

      stubScroll(0, 400, 1000);
      component['onDragStarted'](widget, dragEvent(element) as unknown as CdkDragStart);

      stubScroll(100, 400, 1000);
      component['onFieldScroll']();

      expect(element.style.translate).toBe("0 100px");
      expect(component['dragTarget']()).not.toBeNull();
    });
  });

  describe("toolbar actions", () => {
    it("should begin a staged edit when entering edit mode", () => {
      const beginSpy = jest.spyOn(layoutService, "beginEdit");
      component['enterEdit']();
      expect(beginSpy).toHaveBeenCalled();
      expect(layoutService.editMode()).toBe(true);
    });

    it("should commit the staged edit on save", () => {
      const saveSpy = jest.spyOn(layoutService, "saveEdit");
      component['enterEdit']();
      component['save']();
      expect(saveSpy).toHaveBeenCalled();
      expect(layoutService.editMode()).toBe(false);
    });

    it("should discard the staged edit on cancel", () => {
      const cancelSpy = jest.spyOn(layoutService, "cancelEdit");
      component['enterEdit']();
      component['cancel']();
      expect(cancelSpy).toHaveBeenCalled();
      expect(layoutService.editMode()).toBe(false);
    });
  });
});
