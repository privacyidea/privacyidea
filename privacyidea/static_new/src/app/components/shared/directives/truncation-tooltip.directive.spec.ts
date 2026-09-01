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
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTooltip } from "@angular/material/tooltip";
import { TruncationTooltipDirective } from "./truncation-tooltip.directive";

@Component({
  standalone: true,
  imports: [TruncationTooltipDirective],
  template: `
    <span
      class="with-text"
      [appTruncationTooltip]="text()">
      {{ text() }}
    </span>
    <span
      class="with-icon"
      [appTruncationTooltip]="text()">
      {{ text() }}<i class="icon">unfold_more</i>
    </span>
    <!-- A host that wraps a focusable element, as the dashboard widgets' clipped cells do: only there can focus land
         inside the host, so only there does the focus path apply. -->
    <span
      class="with-link"
      [appTruncationTooltip]="text()">
      <a href="#">{{ text() }}</a>
    </span>
  `
})
class HostComponent {
  readonly text = signal("a very long resolver name");
}

describe("TruncationTooltipDirective", () => {
  let fixture: ComponentFixture<HostComponent>;

  const setWidths = (element: HTMLElement, scrollWidth: number, clientWidth: number): void => {
    Object.defineProperty(element, "scrollWidth", { value: scrollWidth, configurable: true });
    Object.defineProperty(element, "clientWidth", { value: clientWidth, configurable: true });
  };

  const tooltipOf = (selector: string): MatTooltip =>
    fixture.debugElement.query((node) => node.nativeElement?.classList?.contains(selector)).injector.get(MatTooltip);

  const elementOf = (selector: string): HTMLElement => fixture.nativeElement.querySelector(`.${selector}`);

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("shows the full text when the content is truncated", () => {
    const element = elementOf("with-text");
    setWidths(element, 300, 100);

    element.dispatchEvent(new MouseEvent("mouseenter"));

    const tooltip = tooltipOf("with-text");
    expect(tooltip.disabled).toBe(false);
    expect(tooltip.message).toBe("a very long resolver name");
  });

  it("opens on the very first hover", () => {
    jest.useFakeTimers();
    const element = elementOf("with-text");
    setWidths(element, 300, 100);

    element.dispatchEvent(new MouseEvent("mouseenter"));
    jest.runOnlyPendingTimers();

    expect(tooltipOf("with-text")._isTooltipVisible()).toBe(true);
    jest.useRealTimers();
  });

  it("waits for the pointer to rest before opening", () => {
    jest.useFakeTimers();
    const element = elementOf("with-text");
    setWidths(element, 300, 100);

    element.dispatchEvent(new MouseEvent("mouseenter"));
    jest.advanceTimersByTime(400);
    // Still nothing: a pointer merely passing over the element must not pop a tooltip.
    expect(tooltipOf("with-text")._isTooltipVisible()).toBe(false);

    jest.advanceTimersByTime(100);
    expect(tooltipOf("with-text")._isTooltipVisible()).toBe(true);
    jest.useRealTimers();
  });

  it("drops a pending tooltip when the pointer moves on before the delay is up", () => {
    jest.useFakeTimers();
    const element = elementOf("with-text");
    setWidths(element, 300, 100);

    element.dispatchEvent(new MouseEvent("mouseenter"));
    jest.advanceTimersByTime(200);
    element.dispatchEvent(new MouseEvent("mouseleave"));
    jest.runOnlyPendingTimers();

    expect(tooltipOf("with-text")._isTooltipVisible()).toBe(false);
    jest.useRealTimers();
  });

  it("opens without the delay when focus reaches inside the host", () => {
    jest.useFakeTimers();
    const element = elementOf("with-link");
    setWidths(element, 300, 100);

    // Real focus, not a synthetic focusin: it reaches the host only because the host wraps a focusable child like this
    // link. A clipped leaf value such as plain table-cell text has no focus path and needs none, since its full string
    // already sits in the DOM.
    element.querySelector("a")!.focus();
    jest.advanceTimersByTime(0);

    expect(tooltipOf("with-link")._isTooltipVisible()).toBe(true);
    jest.useRealTimers();
  });

  it("closes again when the pointer leaves", () => {
    jest.useFakeTimers();
    const element = elementOf("with-text");
    setWidths(element, 300, 100);
    element.dispatchEvent(new MouseEvent("mouseenter"));
    jest.runOnlyPendingTimers();

    element.dispatchEvent(new MouseEvent("mouseleave"));
    jest.runOnlyPendingTimers();

    expect(tooltipOf("with-text")._isTooltipVisible()).toBe(false);
    jest.useRealTimers();
  });

  it("stays disabled when the content fits", () => {
    const element = elementOf("with-text");
    setWidths(element, 100, 100);

    element.dispatchEvent(new MouseEvent("mouseenter"));

    const tooltip = tooltipOf("with-text");
    expect(tooltip.disabled).toBe(true);
    expect(tooltip.message).toBe("");
  });

  it("shows the bound text only, never the rendered icon content", () => {
    const element = elementOf("with-icon");
    setWidths(element, 300, 100);

    element.dispatchEvent(new MouseEvent("focusin"));

    const tooltip = tooltipOf("with-icon");
    expect(tooltip.disabled).toBe(false);
    expect(tooltip.message).toBe("a very long resolver name");
  });

  it("detects sub-pixel truncation that scrollWidth rounds away", () => {
    const element = elementOf("with-text");
    setWidths(element, 100, 100);
    element.getBoundingClientRect = () => ({ width: 100 }) as DOMRect;
    jest.spyOn(Range.prototype, "getBoundingClientRect").mockReturnValue({ width: 100.6 } as DOMRect);

    element.dispatchEvent(new MouseEvent("mouseenter"));

    expect(tooltipOf("with-text").disabled).toBe(false);
  });

  it("stays disabled when the content fits within a fraction of a pixel", () => {
    const element = elementOf("with-text");
    setWidths(element, 100, 100);
    element.getBoundingClientRect = () => ({ width: 100 }) as DOMRect;
    jest.spyOn(Range.prototype, "getBoundingClientRect").mockReturnValue({ width: 100.2 } as DOMRect);

    element.dispatchEvent(new MouseEvent("mouseenter"));

    expect(tooltipOf("with-text").disabled).toBe(true);
  });

  it("re-evaluates on every hover", () => {
    const element = elementOf("with-text");
    setWidths(element, 300, 100);
    element.dispatchEvent(new MouseEvent("mouseenter"));
    expect(tooltipOf("with-text").disabled).toBe(false);

    setWidths(element, 100, 100);
    element.dispatchEvent(new MouseEvent("mouseenter"));

    expect(tooltipOf("with-text").disabled).toBe(true);
  });
});
