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
import { Directive, ElementRef, HostListener, Renderer2 } from "@angular/core";

@Directive({
  selector: "[appScrollToTop]",
  standalone: true
})
export class ScrollToTopDirective {
  private readonly SCROLL_THRESHOLD = 200;
  private button!: HTMLElement;
  private isButtonVisible = false;

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

  private createButton() {
    this.button = this.renderer.createElement("button");
    this.renderer.addClass(this.button, "scroll-button");

    const icon = this.renderer.createElement("mat-icon");
    this.renderer.addClass(icon, "material-icons");
    this.renderer.setProperty(icon, "innerHTML", "arrow_upward");

    this.renderer.appendChild(this.button, icon);

    this.renderer.setStyle(this.button, "position", "sticky");
    this.renderer.setStyle(this.button, "bottom", "0px");
    this.renderer.setStyle(this.button, "right", "0px");
    this.renderer.setStyle(this.button, "cursor", "pointer");
    this.renderer.setStyle(this.button, "order", "999");
    this.renderer.setStyle(this.button, "width", "4rem");
    this.renderer.setStyle(this.button, "aspect-ratio", "1.618");
    this.renderer.setStyle(this.button, "display", "none");

    // Align the button to the right side of its grid cell
    this.renderer.setStyle(this.button, "justify-self", "end");

    this.renderer.listen(this.button, "click", () => {
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
