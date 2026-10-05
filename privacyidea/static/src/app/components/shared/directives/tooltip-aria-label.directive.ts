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

import { AfterViewInit, Directive, DoCheck, ElementRef, inject } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";

// An icon-only button or link names itself with its tooltip: Material's tooltip describes the element
// (aria-describedby) but gives it no name, so a button holding just an icon would be announced as "button". The
// directive copies the tooltip's message into aria-label, tracking it when it changes. An element that sets its own
// aria-label or aria-labelledby, or that has visible text of its own, keeps what it has.
@Directive({
  selector: "button[matTooltip], a[matTooltip]",
  standalone: true
})
export class TooltipAriaLabelDirective implements AfterViewInit, DoCheck {
  private readonly host: HTMLElement = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly tooltip = inject(MatTooltip, { self: true });
  private enabled = false;
  private applied: string | undefined;

  ngAfterViewInit(): void {
    this.enabled =
      !this.host.hasAttribute("aria-label") &&
      !this.host.hasAttribute("aria-labelledby") &&
      !TooltipAriaLabelDirective.hasVisibleText(this.host);
    if (this.enabled) {
      this.sync();
    }
  }

  ngDoCheck(): void {
    if (this.enabled) {
      this.sync();
    }
  }

  private sync(): void {
    const message = this.tooltip.message?.trim();
    if (message === this.applied) {
      return;
    }
    this.applied = message;
    if (message) {
      this.host.setAttribute("aria-label", message);
    } else {
      this.host.removeAttribute("aria-label");
    }
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
