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
import { AfterViewInit, Directive, ElementRef, inject, NgZone, OnDestroy, Renderer2 } from "@angular/core";

@Directive({
  selector: "[appOverflowNav]",
  standalone: true
})
export class OverflowNavDirective implements AfterViewInit, OnDestroy {
  private el = inject(ElementRef<HTMLElement>);
  private ngZone = inject(NgZone);
  private renderer = inject(Renderer2);
  private resizeObserver: ResizeObserver | null = null;
  private mutationObserver: MutationObserver | null = null;
  private moreButton: HTMLElement | null = null;
  private menuContainer: HTMLElement | null = null;
  private isMenuOpen = false;
  private isCalculating = false;
  private unlisteners: (() => void)[] = [];
  private menuItemUnlisteners: (() => void)[] = [];

  ngAfterViewInit(): void {
    this.createMoreButton();
    this.setupObservers();
    setTimeout(() => this.calculateOverflow(), 50);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.mutationObserver?.disconnect();
    this.unlisteners.forEach(fn => fn());
    this.menuItemUnlisteners.forEach(fn => fn());
    this.removeMenu();
  }

  private createMoreButton(): void {
    const container = this.el.nativeElement;

    this.moreButton = this.renderer.createElement("button");
    this.renderer.setAttribute(this.moreButton, "type", "button");
    this.renderer.setStyle(this.moreButton, "cursor", "pointer");
    this.renderer.addClass(this.moreButton, "overflow-more-btn");
    this.renderer.addClass(this.moreButton, "nav-button");
    this.renderer.addClass(this.moreButton, "mdc-button");
    this.renderer.addClass(this.moreButton, "mat-mdc-button");

    const icon = this.renderer.createElement("mat-icon");
    this.renderer.addClass(icon, "mat-icon");
    this.renderer.addClass(icon, "notranslate");
    this.renderer.addClass(icon, "material-icons");
    this.renderer.addClass(icon, "mat-ligature-font");
    icon.textContent = "more_horiz";
    this.renderer.appendChild(this.moreButton, icon);

    const label = this.renderer.createElement("span");
    label.textContent = $localize`:@@overflowNavMoreLabel:More`;
    this.renderer.appendChild(this.moreButton, label);
    this.renderer.addClass(this.moreButton, "overflow-more-hidden");
    this.renderer.setStyle(this.moreButton, "flex-shrink", "0");

    this.menuContainer = this.renderer.createElement("div");
    this.renderer.addClass(this.menuContainer, "overflow-dropdown");
    this.renderer.setStyle(this.menuContainer, "display", "none");

    this.unlisteners.push(
      this.renderer.listen(this.moreButton, "click", (e: Event) => {
        e.stopPropagation();
        this.toggleMenu();
      })
    );

    this.unlisteners.push(
      this.renderer.listen(this.moreButton, "keydown", (e: KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this.toggleMenu();
        }
      })
    );

    this.unlisteners.push(
      this.renderer.listen("document", "click", () => {
        if (this.isMenuOpen) {
          this.closeMenu();
        }
      })
    );

    const spacer = container.querySelector(".spacer");
    if (spacer) {
      this.renderer.insertBefore(container, this.moreButton, spacer);
    } else {
      this.renderer.appendChild(container, this.moreButton);
    }

    this.renderer.appendChild(document.body, this.menuContainer);
  }

  private setupObservers(): void {
    const container = this.el.nativeElement;

    this.resizeObserver = new ResizeObserver(() => {
      if (!this.isCalculating) {
        this.ngZone.run(() => this.calculateOverflow());
      }
    });
    this.resizeObserver.observe(container);

    this.mutationObserver = new MutationObserver((mutations) => {
      if (this.isCalculating) return;
      const hasRelevantChange = mutations.some(m => {
        if (m.type === "childList" && (m.addedNodes.length > 0 || m.removedNodes.length > 0)) {
          return true;
        }
        if (m.type === "attributes" && m.attributeName === "class") {
          const el = m.target as HTMLElement;
          if (el === this.moreButton) return false;
          if (el.tagName === "A" || el.tagName === "BUTTON") {
            const oldVal = m.oldValue || "";
            const newVal = el.className || "";
            const hadActive = oldVal.includes("sub-nav-active") || oldVal.includes("nav-active");
            const hasActive = newVal.includes("sub-nav-active") || newVal.includes("nav-active");
            return hadActive !== hasActive;
          }
        }
        return false;
      });
      if (hasRelevantChange) {
        this.ngZone.run(() => this.calculateOverflow());
      }
    });
    this.mutationObserver.observe(container, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["class"],
      attributeOldValue: true
    });
  }

  private calculateOverflow(): void {
    if (this.isCalculating || !this.moreButton) return;
    this.isCalculating = true;

    try {
      const container = this.el.nativeElement;
      const buttons = this.getNavButtons();

      if (buttons.length === 0) {
        this.renderer.addClass(this.moreButton, "overflow-more-hidden");
        this.closeMenu();
        return;
      }

      this.renderer.setStyle(container, "overflow", "visible");

      buttons.forEach(btn => {
        this.renderer.removeStyle(btn, "display");
        this.renderer.removeClass(btn, "sub-overflow-hidden");
      });
      this.renderer.removeClass(container, "is-overflowing");
      this.renderer.addClass(this.moreButton, "overflow-more-hidden");

      const containerWidth = container.clientWidth;

      const getWidthWithMargins = (el: HTMLElement) => {
        const style = window.getComputedStyle(el);
        const marginLeft = parseFloat(style.marginLeft) || 0;
        const marginRight = parseFloat(style.marginRight) || 0;
        return el.offsetWidth + marginLeft + marginRight;
      };

      let leftReserved = 16;
      const firstNavButton = buttons[0];
      let currentEl = container.firstElementChild as HTMLElement;
      while (currentEl && currentEl !== firstNavButton && currentEl !== this.moreButton && !currentEl.classList.contains("spacer")) {
        const style = window.getComputedStyle(currentEl);
        if (style.display !== "none" && style.visibility !== "hidden") {
          leftReserved += getWidthWithMargins(currentEl) + 8; // width + gap
        }
        currentEl = currentEl.nextElementSibling as HTMLElement;
      }

      let rightWidth = 16;
      const spacer = container.querySelector(".spacer");
      if (spacer) {
        let el = spacer.nextElementSibling;
        while (el) {
          if (el !== this.moreButton && el !== this.menuContainer) {
            const style = window.getComputedStyle(el);
            if (style.display !== "none" && style.visibility !== "hidden") {
              rightWidth += getWidthWithMargins(el as HTMLElement) + 8;
            }
          }
          el = el.nextElementSibling;
        }
      }

      this.renderer.setStyle(container, "overflow", "hidden");

      const wasHidden = this.moreButton.classList.contains("overflow-more-hidden");
      this.renderer.removeClass(this.moreButton, "overflow-more-hidden");
      const moreButtonWidth = getWidthWithMargins(this.moreButton) || 160;
      if (wasHidden) {
        this.renderer.addClass(this.moreButton, "overflow-more-hidden");
      }

      const gap = 8;
      const availableForButtons = containerWidth - leftReserved - rightWidth - 40;

      const activeIndex = buttons.findIndex(btn =>
        btn.classList.contains("sub-nav-active") || btn.classList.contains("nav-active")
      );

      let usedWidth = 0;
      const visible: boolean[] = new Array(buttons.length).fill(false);

      let totalWidth = buttons.reduce((sum, btn) => sum + btn.offsetWidth, 0);
      if (buttons.length > 0) {
        totalWidth += (buttons.length - 1) * gap;
      }

      if (totalWidth <= availableForButtons) {
        visible.fill(true);
      } else {
        const maxWidthWithMore = availableForButtons - moreButtonWidth;

        if (activeIndex >= 0) {
          const activeBtnWidth = buttons[activeIndex].offsetWidth + gap;
          if (activeBtnWidth <= maxWidthWithMore) {
            usedWidth += activeBtnWidth;
            visible[activeIndex] = true;
          }
        }

        for (let i = 0; i < buttons.length; i++) {
          if (i === activeIndex) continue;
          const btnWidth = buttons[i].offsetWidth + gap;

          if (usedWidth + btnWidth <= maxWidthWithMore) {
            usedWidth += btnWidth;
            visible[i] = true;
          } else {
            break;
          }
        }
      }

      const hiddenButtons = buttons.filter((_, i) => !visible[i]);

      if (hiddenButtons.length > 0) {
        this.renderer.addClass(container, "is-overflowing");
        hiddenButtons.forEach(btn => {
          this.renderer.addClass(btn, "sub-overflow-hidden");
          this.renderer.setStyle(btn, "display", "none");
        });
        this.renderer.removeClass(this.moreButton, "overflow-more-hidden");
        this.updateMenuContent(hiddenButtons);
      } else {
        this.renderer.removeClass(container, "is-overflowing");
        this.renderer.addClass(this.moreButton, "overflow-more-hidden");
        this.closeMenu();
      }
    } finally {
      this.isCalculating = false;
    }
  }

  private getNavButtons(): HTMLElement[] {
    const container = this.el.nativeElement;
    const all = Array.from(container.children) as HTMLElement[];
    return all.filter(el =>
      el !== this.moreButton &&
      (el.tagName === "BUTTON" || el.tagName === "A") &&
      !el.classList.contains("overflow-more-btn") &&
      !el.closest(".spacer") &&
      !this.isAfterSpacer(el)
    );
  }

  private isAfterSpacer(el: HTMLElement): boolean {
    const container = this.el.nativeElement;
    const spacer = container.querySelector(".spacer");
    if (!spacer) return false;
    return !!(spacer.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING);
  }


  private updateMenuContent(hiddenButtons: HTMLElement[]): void {
    if (!this.menuContainer) return;

    this.menuItemUnlisteners.forEach(fn => fn());
    this.menuItemUnlisteners = [];

    this.menuContainer.innerHTML = "";

    hiddenButtons.forEach(btn => {
      const menuItem = this.renderer.createElement("button");
      this.renderer.setAttribute(menuItem, "type", "button");
      this.renderer.setStyle(menuItem, "text-decoration", "none");
      this.renderer.addClass(menuItem, "overflow-menu-item");
      if (btn.classList.contains("sub-nav-active") || btn.classList.contains("nav-active")) {
        this.renderer.addClass(menuItem, "overflow-menu-item-active");
      }

      const icon = btn.querySelector("mat-icon");
      if (icon) {
        const iconElem = this.renderer.createElement("mat-icon");
        this.renderer.addClass(iconElem, "mat-icon");
        this.renderer.addClass(iconElem, "notranslate");
        this.renderer.addClass(iconElem, "material-icons");
        this.renderer.addClass(iconElem, "mat-ligature-font");
        iconElem.textContent = icon.textContent?.trim() || "";
        icon.classList.forEach((cls: string) => {
          if (cls.startsWith("ms--") || cls.startsWith("mdi--")) {
            this.renderer.addClass(iconElem, cls);
          }
        });
        this.renderer.appendChild(menuItem, iconElem);
      }

      const spans = btn.querySelectorAll("span");
      let textContent = "";
      spans.forEach(s => {
        if (!s.classList.contains("mat-mdc-button-touch-target") &&
          !s.classList.contains("mdc-button__label") &&
          !s.classList.contains("mat-mdc-focus-indicator") &&
          !s.classList.contains("mat-ripple")) {
          const t = s.textContent?.trim();
          if (t) textContent = t;
        }
      });
      if (!textContent) {
        textContent = btn.textContent?.trim() || "";
      }

      const label = this.renderer.createElement("span");
      label.textContent = textContent;
      this.renderer.appendChild(menuItem, label);

      this.menuItemUnlisteners.push(
        this.renderer.listen(menuItem, "click", (e: Event) => {
          e.stopPropagation();
          btn.click();
          this.closeMenu();
        })
      );

      this.renderer.appendChild(this.menuContainer, menuItem);
    });
  }

  private toggleMenu(): void {
    if (this.isMenuOpen) {
      this.closeMenu();
    } else {
      this.openMenu();
    }
  }

  private openMenu(): void {
    if (!this.menuContainer || !this.moreButton) return;

    const rect = this.moreButton.getBoundingClientRect();
    this.renderer.setStyle(this.menuContainer, "position", "fixed");
    this.renderer.setStyle(this.menuContainer, "top", `${rect.bottom + 4}px`);
    this.renderer.setStyle(this.menuContainer, "left", `${rect.left}px`);
    this.renderer.setStyle(this.menuContainer, "display", "block");
    this.isMenuOpen = true;
  }

  private closeMenu(): void {
    if (!this.menuContainer) return;
    this.renderer.setStyle(this.menuContainer, "display", "none");
    this.isMenuOpen = false;
  }

  private removeMenu(): void {
    if (this.menuContainer && this.menuContainer.parentNode) {
      this.menuContainer.parentNode.removeChild(this.menuContainer);
    }
  }
}



