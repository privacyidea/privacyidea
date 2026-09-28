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
// under either of two conditions: once the table's header is stuck (.table-scroll-region
// scrolled-from-top, a sibling of this paginator's own .filter-paginator-container), or - just as
// much a "not enough room" signal - whenever the row is tight enough that the filter field next to
// it (inside .filter-actions-group, the container's other child) has no slack left. Material renders
// the whole phrase as one interpolated text node with no separate markup for the range and the
// total, so it can't be trimmed with CSS alone; this rewrites the node by hand instead, in either
// direction, so it stays correct whether the rewrite runs during ngDoCheck (a genuine page change)
// or from one of this directive's own observers (scroll/resize, neither of which goes through
// Angular change detection on their own).
@Directive({
  selector: "mat-paginator[appPaginatorCompactRange]",
  standalone: true
})
export class PaginatorCompactRangeDirective implements AfterViewInit, DoCheck, OnDestroy {
  // The gap between .filter-actions-group and this paginator (container width minus both their
  // rendered widths) has to clear this margin before switching back to the full label - not just
  // reach zero. Switching eats back into that same gap by roughly the width of " of 10,189" at this
  // app's usual number formats and font size, so a release threshold at or near zero would have the
  // switch immediately re-close the gap it just measured as sufficient, flip back to compact, reopen
  // the gap, flip back to full, forever. This only needs to be a safe upper bound on that width, not
  // exact - and it must clear the ENGAGE_GAP_PX margin below by a wide margin, or the same loop
  // reappears from the other direction.
  private static readonly RELEASE_GAP_PX = 120;
  // The gap has to run out (drop below this) before switching to compact - a small positive margin
  // rather than zero, so the switch happens just ahead of the row actually running out of room
  // instead of after.
  private static readonly ENGAGE_GAP_PX = 8;

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly paginator = inject(MatPaginator);
  private readonly intl = inject(MatPaginatorIntl);
  private label?: HTMLElement;
  private scrollRegion?: Element;
  private container?: HTMLElement;
  private filterActionsGroup?: HTMLElement;
  private classObserver?: MutationObserver;
  private resizeObserver?: ResizeObserver;
  private writingBack = false;
  private compact = false;

  ngAfterViewInit(): void {
    const label = this.host.nativeElement.querySelector<HTMLElement>(".mat-mdc-paginator-range-label");
    const container = this.host.nativeElement.closest<HTMLElement>(".filter-paginator-container");
    const scrollRegion = container?.parentElement?.querySelector(":scope > .table-scroll-region");
    if (!label || !container || !scrollRegion) {
      return;
    }
    this.label = label;
    this.container = container;
    this.scrollRegion = scrollRegion;
    this.filterActionsGroup = container.querySelector<HTMLElement>(":scope > .filter-actions-group") ?? undefined;

    // ScrollEdgesDirective toggles scrolled-from-top via Renderer2, which does not go through
    // Angular change detection, so this label needs its own observer to notice it.
    this.classObserver = new MutationObserver(() => this.apply());
    this.classObserver.observe(scrollRegion, { attributes: true, attributeFilter: ["class"] });

    // The row's available space changes with the viewport (including a browser zoom level, which
    // reflows exactly like a narrower viewport would) independently of any class toggling.
    this.resizeObserver = new ResizeObserver(() => this.apply());
    this.resizeObserver.observe(container);

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
    this.resizeObserver?.disconnect();
  }

  private apply(): void {
    if (this.writingBack || !this.label || !this.scrollRegion) {
      return;
    }
    const scrolled = this.scrollRegion.classList.contains("scrolled-from-top");
    this.compact = scrolled || this.isRowTight();
    const text = this.compact
      ? getCompactRangeLabel(this.paginator.pageIndex, this.paginator.pageSize, this.paginator.length)
      : this.intl.getRangeLabel(this.paginator.pageIndex, this.paginator.pageSize, this.paginator.length);
    if (this.label.textContent === text) {
      return;
    }
    this.writingBack = true;
    this.label.textContent = text;
    this.writingBack = false;
  }

  // Reads current rendered widths only - never writes to the label to measure a hypothetical one.
  // Deciding by mutating the label first (to force its widest state before reading) was tried and
  // reverted: the "did anything actually change" check further up can only compare against the
  // label's live content, so a measurement step that alters that same content as a side effect
  // defeats its own guard - every call then looks like a change, every call rewrites the label, and
  // every rewrite runs straight back into ngDoCheck on the next change-detection pass, forever.
  //
  // Measures the gap between the filter field's group and this paginator, not the group's (or the
  // filter field's) own width against its max-width: both are capped by CSS, so once either is fully
  // grown, its width sits at that cap and can never report the row having any further slack beyond
  // it, however wide the viewport actually is - checking a capped value against itself can only ever
  // detect "squeezed" and would latch compact permanently the first time it engaged.
  private isRowTight(): boolean {
    if (!this.container || !this.filterActionsGroup) {
      return false;
    }
    const containerWidth = this.container.getBoundingClientRect().width;
    const groupWidth = this.filterActionsGroup.getBoundingClientRect().width;
    const paginatorWidth = this.host.nativeElement.getBoundingClientRect().width;
    // A real, rendered row is never literally zero-width on every one of its three measured
    // elements at once - that combination only happens where no layout engine ran at all (unit
    // tests under jsdom), which would otherwise read as an infinitely tight row and permanently
    // force compact mode in any test that renders a real paginator with this directive attached.
    if (containerWidth === 0 && groupWidth === 0 && paginatorWidth === 0) {
      return false;
    }
    const gap = containerWidth - groupWidth - paginatorWidth;
    const threshold = this.compact
      ? PaginatorCompactRangeDirective.RELEASE_GAP_PX
      : PaginatorCompactRangeDirective.ENGAGE_GAP_PX;
    return gap < threshold;
  }
}
