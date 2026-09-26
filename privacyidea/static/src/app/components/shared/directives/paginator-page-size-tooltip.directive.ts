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
import { AfterViewInit, Directive, ElementRef, inject, Injector, OnDestroy, Renderer2 } from "@angular/core";
import { MatPaginatorIntl } from "@angular/material/paginator";
import { MatTooltip } from "@angular/material/tooltip";

// Material always renders the "Items per page" label as visible text next to the size picker.
// Combined with .hide-page-size-label (table-global.scss) hiding that text, this puts the same
// label on the picker as a real matTooltip instead. mat-select's own trigger sits inside
// mat-paginator's internal template, which is not ours to add matTooltip to directly, so MatTooltip
// is instantiated by hand here - via Injector.create, not `hostDirectives`, so it can be bound to
// the size picker's own element and anchor there instead of to the whole (much wider) paginator.
// It is shown and hidden by hand too: Material lays a transparent .mat-mdc-paginator-touch-target
// on top of the select to enlarge its hit area, so that, not the select, is what actually receives
// the hover.
@Directive({
  selector: "mat-paginator[appPaginatorPageSizeTooltip]",
  standalone: true
})
export class PaginatorPageSizeTooltipDirective implements AfterViewInit, OnDestroy {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly intl = inject(MatPaginatorIntl);
  private readonly renderer = inject(Renderer2);
  private readonly parentInjector = inject(Injector);
  private readonly cleanup: (() => void)[] = [];
  private tooltip?: MatTooltip;

  ngAfterViewInit(): void {
    const pageSize = this.host.nativeElement.querySelector<HTMLElement>(".mat-mdc-paginator-page-size");
    const target = pageSize?.querySelector<HTMLElement>(".mat-mdc-paginator-touch-target") ?? pageSize;
    if (!target) {
      return;
    }

    const injector = Injector.create({
      parent: this.parentInjector,
      providers: [{ provide: ElementRef, useValue: new ElementRef(target) }, MatTooltip]
    });
    const tooltip = injector.get(MatTooltip);
    tooltip.position = "below";
    tooltip.message = this.intl.itemsPerPageLabel.replace(/:\s*$/, "");
    this.tooltip = tooltip;

    this.cleanup.push(
      this.renderer.listen(target, "mouseenter", () => tooltip.show()),
      this.renderer.listen(target, "mouseleave", () => tooltip.hide()),
      this.renderer.listen(target, "focusin", () => tooltip.show()),
      this.renderer.listen(target, "focusout", () => tooltip.hide())
    );
  }

  ngOnDestroy(): void {
    this.cleanup.forEach((unlisten) => unlisten());
    this.tooltip?.ngOnDestroy();
  }
}
