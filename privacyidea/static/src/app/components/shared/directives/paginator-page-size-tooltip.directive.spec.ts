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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatPaginatorIntl, MatPaginatorModule } from "@angular/material/paginator";
import { MatTooltip } from "@angular/material/tooltip";
import { PaginatorPageSizeTooltipDirective } from "./paginator-page-size-tooltip.directive";

@Component({
  standalone: true,
  imports: [MatPaginatorModule, PaginatorPageSizeTooltipDirective],
  template: ` <mat-paginator
    appPaginatorPageSizeTooltip
    [length]="100"
    [pageSize]="10"
    [pageSizeOptions]="[10, 25, 50]"></mat-paginator> `
})
class HostComponent {}

describe("PaginatorPageSizeTooltipDirective", () => {
  let fixture: ComponentFixture<HostComponent>;

  const touchTarget = (): HTMLElement =>
    fixture.nativeElement.querySelector(".mat-mdc-paginator-page-size .mat-mdc-paginator-touch-target");

  // The directive instantiates MatTooltip by hand via Injector.create, off Angular's own component
  // injector tree, so it never shows up as a provider on the touch target's own DebugElement - the
  // directive's own (private) reference is the only way to reach it from a test.
  const tooltip = (): MatTooltip =>
    (
      fixture.debugElement.query(By.directive(PaginatorPageSizeTooltipDirective)).injector.get(
        PaginatorPageSizeTooltipDirective
      ) as unknown as { tooltip: MatTooltip }
    ).tooltip;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it("anchors a tooltip to the page-size touch target with the intl label", () => {
    const intl = TestBed.inject(MatPaginatorIntl);

    expect(tooltip().position).toBe("below");
    expect(tooltip().message).toBe(intl.itemsPerPageLabel.replace(/:\s*$/, ""));
  });

  it("shows the tooltip on mouseenter and hides it on mouseleave", () => {
    jest.useFakeTimers();
    const target = touchTarget();

    target.dispatchEvent(new MouseEvent("mouseenter"));
    jest.runOnlyPendingTimers();
    expect(tooltip()._isTooltipVisible()).toBe(true);

    target.dispatchEvent(new MouseEvent("mouseleave"));
    jest.runOnlyPendingTimers();
    expect(tooltip()._isTooltipVisible()).toBe(false);
    jest.useRealTimers();
  });

  it("shows the tooltip on focusin and hides it on focusout", () => {
    jest.useFakeTimers();
    const target = touchTarget();

    target.dispatchEvent(new FocusEvent("focusin"));
    jest.runOnlyPendingTimers();
    expect(tooltip()._isTooltipVisible()).toBe(true);

    target.dispatchEvent(new FocusEvent("focusout"));
    jest.runOnlyPendingTimers();
    expect(tooltip()._isTooltipVisible()).toBe(false);
    jest.useRealTimers();
  });

  it("removes its listeners and destroys the tooltip on destroy", () => {
    const target = touchTarget();
    const activeTooltip = tooltip();
    const destroySpy = jest.spyOn(activeTooltip, "ngOnDestroy");

    fixture.destroy();

    expect(destroySpy).toHaveBeenCalled();
    target.dispatchEvent(new MouseEvent("mouseenter"));
    expect(activeTooltip._isTooltipVisible()).toBe(false);
  });
});
