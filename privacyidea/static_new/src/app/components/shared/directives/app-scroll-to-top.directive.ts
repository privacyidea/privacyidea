/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Directive, ElementRef, HostListener, OnDestroy, Renderer2 } from "@angular/core";

@Directive({
  selector: "[appScrollToTop]",
  standalone: true
})
export class ScrollToTopDirective implements OnDestroy {
  private readonly SCROLL_THRESHOLD = 200;
  private button!: HTMLElement;
  private isButtonVisible = false;
  private clickListenerDispose?: () => void;

  constructor(
    private el: ElementRef,
    private renderer: Renderer2
  ) {
    this.createButton();
  }

  @HostListener("scroll")
  onScroll() {
    const scrollContainer = this.el.nativeElement as HTMLElement;
    const isScrolled = scrollContainer.scrollTop > this.SCROLL_THRESHOLD;

    if (isScrolled && !this.isButtonVisible) {
      this.showButton();
    } else if (!isScrolled && this.isButtonVisible) {
      this.hideButton();
    }
  }

  ngOnDestroy() {
    if (this.clickListenerDispose) {
      this.clickListenerDispose();
    }
  }

  private createButton() {
    this.button = this.renderer.createElement("button");
    this.renderer.addClass(this.button, "mat-fab");
    this.renderer.addClass(this.button, "scroll-to-top-fab");

    const icon = this.renderer.createElement("mat-icon");
    this.renderer.addClass(icon, "material-icons");
    this.renderer.addClass(icon, "scroll-to-top-fab-icon");
    this.renderer.setProperty(icon, "innerHTML", "keyboard_arrow_upward");

    this.renderer.appendChild(this.button, icon);

    this.renderer.setStyle(this.button, "position", "sticky");
    this.renderer.setStyle(this.button, "bottom", "0px");
    this.renderer.setStyle(this.button, "cursor", "pointer");
    this.renderer.setStyle(this.button, "order", "999");
    this.renderer.setStyle(this.button, "aspect-ratio", "1");
    this.renderer.setStyle(this.button, "display", "none");
    this.renderer.setStyle(this.button, "margin-right", "64px");

    // Align the button to the right side of its grid cell
    this.renderer.setStyle(this.button, "justify-self", "end");

    this.clickListenerDispose = this.renderer.listen(this.button, "click", () => {
      this.el.nativeElement.scrollTo({
        top: 0,
        behavior: "smooth"
      });
    });

    this.renderer.appendChild(this.el.nativeElement, this.button);
    this.onScroll();
  }

  private showButton() {
    this.renderer.setStyle(this.button, "display", "block");
    this.isButtonVisible = true;
  }

  private hideButton() {
    this.renderer.setStyle(this.button, "display", "none");
    this.isButtonVisible = false;
  }
}
