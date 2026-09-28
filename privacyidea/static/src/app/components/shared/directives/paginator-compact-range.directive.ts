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
import { AfterViewInit, Directive, DoCheck, ElementRef, inject, OnDestroy } from "@angular/core";
import { MatPaginator, MatPaginatorIntl } from "@angular/material/paginator";
import { getCompactRangeLabel } from "@app/paginator-intl";

// Of the full "1,066 - 1,080 of 10,189" range label, the current page's own position
// ("1,066 - 1,080") is what the user is actually tracking - the total is the part safe to drop
// once the table's header is stuck (.table-scroll-region scrolled-from-top, a sibling of this
// paginator's own .filter-paginator-container). The row's own width never has to be watched for
// this: .mat-mdc-paginator carries min-width: max-content (table-global.scss), which - as long as
// this directive itself never swaps away from the full label pre-emptively - keeps the row exactly
// as wide as showing that full label needs, wrapping the filter field below it instead of ever
// running out of room. Material renders the whole phrase as one interpolated text node with no
// separate markup for the range and the total, so it can't be trimmed with CSS alone; this rewrites
// the node by hand instead, so it stays correct whether the rewrite runs during ngDoCheck (a genuine
// page change) or from the scroll-class observer below (which does not go through Angular change
// detection on its own).
@Directive({
  selector: "mat-paginator[appPaginatorCompactRange]",
  standalone: true
})
export class PaginatorCompactRangeDirective implements AfterViewInit, DoCheck, OnDestroy {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly paginator = inject(MatPaginator);
  private readonly intl = inject(MatPaginatorIntl);
  private label?: HTMLElement;
  private scrollRegion?: Element;
  private classObserver?: MutationObserver;
  private writingBack = false;

  ngAfterViewInit(): void {
    const label = this.host.nativeElement.querySelector<HTMLElement>(".mat-mdc-paginator-range-label");
    const container = this.host.nativeElement.closest<HTMLElement>(".filter-paginator-container");
    const scrollRegion = container?.parentElement?.querySelector(":scope > .table-scroll-region");
    if (!label || !container || !scrollRegion) {
      return;
    }
    this.label = label;
    this.scrollRegion = scrollRegion;

    // ScrollEdgesDirective toggles scrolled-from-top via Renderer2, which does not go through
    // Angular change detection, so this label needs its own observer to notice it.
    this.classObserver = new MutationObserver(() => this.apply());
    this.classObserver.observe(scrollRegion, { attributes: true, attributeFilter: ["class"] });

    this.apply();
  }

  // Angular re-renders the paginator's own template - including this label - whenever
  // pageIndex/pageSize/length change, as part of the very same change-detection pass that reads
  // those inputs in the first place; ngDoCheck runs on every one of those passes too, so it catches
  // that re-render deterministically instead of watching for it to land in the DOM. That distinction
  // matters beyond just being simpler: a MutationObserver is a real, live browser mechanism, and
  // this project's test setup stubs it out globally as an inert no-op - relying on one here would
  // have frozen this label at whatever it first rendered in every component test that mounts a real
  // paginator with this directive but does not itself know to override that stub.
  ngDoCheck(): void {
    this.apply();
  }

  ngOnDestroy(): void {
    this.classObserver?.disconnect();
  }

  private apply(): void {
    if (this.writingBack || !this.label || !this.scrollRegion) {
      return;
    }
    const compact = this.scrollRegion.classList.contains("scrolled-from-top");
    const text = compact
      ? getCompactRangeLabel(this.paginator.pageIndex, this.paginator.pageSize, this.paginator.length)
      : this.intl.getRangeLabel(this.paginator.pageIndex, this.paginator.pageSize, this.paginator.length);
    if (this.label.textContent === text) {
      return;
    }
    this.writingBack = true;
    this.label.textContent = text;
    this.writingBack = false;
  }
}
