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
import { Directive, ElementRef, inject, input } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";

@Directive({
  selector: "[appTruncationTooltip]",
  standalone: true,
  hostDirectives: [MatTooltip],
  host: {
    "(mouseenter)": "open()",
    "(focusin)": "open()",
    "(mouseleave)": "close()",
    "(focusout)": "close()"
  }
})
export class TruncationTooltipDirective {
  // Put the directive on the element that actually clips its text, not on an ancestor:
  // a wrapper that shrinks around clipped children never overflows itself, so nothing
  // would be detected. The text is always bound explicitly - reading it back from the
  // DOM would pick up icon ligatures and other non-text content.
  readonly text = input.required<string>({ alias: "appTruncationTooltip" });

  private readonly tooltip = inject(MatTooltip);
  private readonly elementRef = inject<ElementRef<HTMLElement>>(ElementRef);

  // MatTooltip attaches its own pointer listeners only once it has a message, which it
  // does not have before the first hover. So the tooltip is opened and closed from here
  // instead of leaving the first hover unanswered.
  protected open(): void {
    this.syncTooltip();
    if (!this.tooltip.disabled) {
      this.tooltip.show();
    }
  }

  protected close(): void {
    this.tooltip.hide();
  }

  private syncTooltip(): void {
    const host = this.elementRef.nativeElement;
    const truncated = this.isTruncated(host);
    const message = this.text();
    this.tooltip.message = truncated ? message : "";
    this.tooltip.disabled = !truncated || !message;
  }

  private isTruncated(host: HTMLElement): boolean {
    if (host.scrollWidth > host.clientWidth) {
      return true;
    }
    const range = document.createRange();
    range.selectNodeContents(host);
    const contentWidth = range.getBoundingClientRect().width;
    if (!contentWidth) {
      return false;
    }
    const style = getComputedStyle(host);
    const px = (value: string): number => parseFloat(value) || 0;
    const available =
      host.getBoundingClientRect().width -
      px(style.paddingLeft) -
      px(style.paddingRight) -
      px(style.borderLeftWidth) -
      px(style.borderRightWidth);
    return contentWidth - available > 0.5;
  }
}
