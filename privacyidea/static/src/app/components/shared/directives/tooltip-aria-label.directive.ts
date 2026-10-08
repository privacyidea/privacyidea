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

import { AfterViewInit, Directive, DoCheck, ElementRef, NgZone, OnDestroy, inject } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";

// An icon-only button or link names itself with its tooltip: Material's tooltip describes the element
// (aria-describedby) but gives it no name, so a button holding just an icon would be announced as "button". The
// directive copies the tooltip's message into aria-label, tracking it when it changes.
//
// The directive owns the aria-label only while it is the one that wrote it:
// - another writer's aria-label or aria-labelledby (set at any time, for example by an [attr.aria-label] binding
//   that turns from null to a value) is never overwritten or removed; the directive steps back until that writer
//   removes its name again.
// - visible text appearing in the element removes the directive's label, so the accessible name always contains
//   the visible text (WCAG 2.5.3); when the text disappears the label is applied again.
// A MutationObserver reports the host's text, its aria-hidden subtree and its two naming attributes, so the check
// costs nothing while the element is unchanged; the tooltip message is compared in ngDoCheck because it has no DOM
// footprint of its own.
@Directive({
  // Attaches to Material's own matTooltip on a button or link, so it takes effect wherever the tooltip does.
  // eslint-disable-next-line @angular-eslint/directive-selector
  selector: "button[matTooltip], a[matTooltip]",
  standalone: true
})
export class TooltipAriaLabelDirective implements AfterViewInit, DoCheck, OnDestroy {
  private readonly host: HTMLElement = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly tooltip = inject(MatTooltip, { self: true });
  private readonly ngZone = inject(NgZone);
  private observer?: MutationObserver;
  private started = false;
  // The aria-label this directive wrote and still owns; undefined while another writer or visible text names the element.
  private applied: string | undefined;
  private lastMessage: string | undefined;

  ngAfterViewInit(): void {
    this.started = true;
    this.update();
    // Outside the zone: an observer callback must not schedule a change detection of its own.
    this.ngZone.runOutsideAngular(() => {
      this.observer = new MutationObserver(() => this.update());
      this.observer.observe(this.host, {
        childList: true,
        characterData: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["aria-label", "aria-labelledby", "aria-hidden"]
      });
    });
  }

  ngDoCheck(): void {
    if (this.started && this.tooltip.message?.trim() !== this.lastMessage) {
      this.update();
    }
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  private update(): void {
    const message = this.tooltip.message?.trim();
    this.lastMessage = message;
    const current = this.host.getAttribute("aria-label");
    const owns = this.applied !== undefined && current === this.applied;
    const namedByOthers =
      this.host.hasAttribute("aria-labelledby") ||
      (current !== null && !owns) ||
      TooltipAriaLabelDirective.hasVisibleText(this.host);

    if (namedByOthers || !message) {
      if (owns) {
        this.host.removeAttribute("aria-label");
      }
      this.applied = undefined;
    } else if (current !== message) {
      this.host.setAttribute("aria-label", message);
      this.applied = message;
    } else {
      this.applied = message;
    }
    // The directive's own writes are already accounted for.
    this.observer?.takeRecords();
  }

  // Text a screen reader would read: anything outside aria-hidden subtrees (an icon's ligature is hidden).
  private static hasVisibleText(node: Node): boolean {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === Node.TEXT_NODE && child.textContent?.trim()) {
        return true;
      }
      if (child instanceof HTMLElement && child.getAttribute("aria-hidden") !== "true") {
        if (TooltipAriaLabelDirective.hasVisibleText(child)) {
          return true;
        }
      }
    }
    return false;
  }
}
