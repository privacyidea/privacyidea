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
import { AfterViewInit, Directive, ElementRef, inject, OnDestroy, Renderer2 } from "@angular/core";

const GAP = 8;
const PADDING = 16;
const EXTRA_MARGIN = 40;
const MAT_ICON_CLASSES = ["mat-icon", "notranslate", "material-icons", "mat-ligature-font"];
const MAT_INTERNAL_SPANS = [
  "mat-mdc-button-touch-target",
  "mdc-button__label",
  "mat-mdc-focus-indicator",
  "mat-ripple"
];

function isActive(el: HTMLElement): boolean {
  return el.classList.contains("sub-nav-active") || el.classList.contains("nav-active");
}

function isVisible(el: HTMLElement): boolean {
  const style = window.getComputedStyle(el);
  return style.display !== "none" && style.visibility !== "hidden";
}

function getOuterWidth(el: HTMLElement): number {
  const style = window.getComputedStyle(el);
  return el.offsetWidth + (parseFloat(style.marginLeft) || 0) + (parseFloat(style.marginRight) || 0);
}

@Directive({
  selector: "[appOverflowNav]",
  standalone: true
})
export class OverflowNavDirective implements AfterViewInit, OnDestroy {
  private el = inject(ElementRef<HTMLElement>);
  private renderer = inject(Renderer2);
  private resizeObserver: ResizeObserver | null = null;
  private mutationObserver: MutationObserver | null = null;
  private moreButton!: HTMLElement;
  private menuContainer!: HTMLElement;
  private isMenuOpen = false;
  private isCalculating = false;
  private unlisteners: (() => void)[] = [];
  private menuItemUnlisteners: (() => void)[] = [];

  private get container(): HTMLElement {
    return this.el.nativeElement;
  }

  private get spacer(): HTMLElement | null {
    return this.container.querySelector(".spacer");
  }

  ngAfterViewInit(): void {
    this.createMoreButton();
    this.setupObservers();
    setTimeout(() => this.calculateOverflow(), 50);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.mutationObserver?.disconnect();
    [...this.unlisteners, ...this.menuItemUnlisteners].forEach((fn) => fn());
    this.menuContainer?.parentNode?.removeChild(this.menuContainer);
  }

  private listen(target: any, event: string, handler: (e: any) => void): void {
    this.unlisteners.push(this.renderer.listen(target, event, handler));
  }

  private createMatIcon(ligature: string, extraClasses: string[] = []): HTMLElement {
    const icon = this.renderer.createElement("mat-icon");
    for (const cls of [...MAT_ICON_CLASSES, ...extraClasses]) {
      this.renderer.addClass(icon, cls);
    }
    icon.textContent = ligature;
    return icon;
  }

  private createMoreButton(): void {
    this.moreButton = this.renderer.createElement("button");
    this.renderer.setAttribute(this.moreButton, "type", "button");
    this.renderer.setStyle(this.moreButton, "cursor", "pointer");
    this.renderer.setStyle(this.moreButton, "flex-shrink", "0");
    for (const cls of ["overflow-more-btn", "nav-button", "mdc-button", "mat-mdc-button", "overflow-more-hidden"]) {
      this.renderer.addClass(this.moreButton, cls);
    }

    this.renderer.appendChild(this.moreButton, this.createMatIcon("more_horiz"));

    const label = this.renderer.createElement("span");
    label.textContent = $localize`:@@overflowNavMoreLabel:More`;
    this.renderer.appendChild(this.moreButton, label);

    this.menuContainer = this.renderer.createElement("div");
    this.renderer.addClass(this.menuContainer, "overflow-dropdown");
    this.renderer.setStyle(this.menuContainer, "display", "none");

    this.listen(this.moreButton, "click", (e: Event) => {
      e.stopPropagation();
      this.toggleMenu();
    });
    this.listen(this.moreButton, "keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        this.toggleMenu();
      }
    });
    this.listen("document", "click", () => {
      if (this.isMenuOpen) this.closeMenu();
    });

    const spacer = this.spacer;
    if (spacer) {
      this.renderer.insertBefore(this.container, this.moreButton, spacer);
    } else {
      this.renderer.appendChild(this.container, this.moreButton);
    }

    this.renderer.appendChild(document.body, this.menuContainer);
  }

  private setupObservers(): void {
    this.resizeObserver = new ResizeObserver(() => {
      if (!this.isCalculating) {
        this.calculateOverflow();
      }
    });
    this.resizeObserver.observe(this.container);

    this.mutationObserver = new MutationObserver((mutations) => {
      if (this.isCalculating) return;
      const hasRelevantChange = mutations.some((m) => {
        if (m.type === "childList" && (m.addedNodes.length > 0 || m.removedNodes.length > 0)) {
          return true;
        }
        if (m.type === "attributes" && m.attributeName === "class") {
          const el = m.target as HTMLElement;
          if (el === this.moreButton) return false;
          if (el.tagName === "A" || el.tagName === "BUTTON") {
            const hadActive = (m.oldValue || "").includes("nav-active");
            const hasNow = (el.className || "").includes("nav-active");
            return hadActive !== hasNow;
          }
        }
        return false;
      });
      if (hasRelevantChange) {
        this.calculateOverflow();
      }
    });
    this.mutationObserver.observe(this.container, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["class"],
      attributeOldValue: true
    });
  }

  private calculateOverflow(): void {
    if (this.isCalculating) return;
    this.isCalculating = true;

    try {
      const buttons = this.getNavButtons();

      if (buttons.length === 0) {
        this.setMoreButtonVisible(false);
        this.closeMenu();
        return;
      }

      this.renderer.setStyle(this.container, "overflow", "visible");
      buttons.forEach((btn) => {
        this.renderer.removeStyle(btn, "display");
        this.renderer.removeClass(btn, "sub-overflow-hidden");
      });
      this.renderer.removeClass(this.container, "is-overflowing");
      this.setMoreButtonVisible(false);

      const containerWidth = this.container.clientWidth;
      const reservedWidth = this.measureReservedWidth(buttons[0]) + EXTRA_MARGIN;
      const availableForButtons = containerWidth - reservedWidth;

      const totalWidth = buttons.reduce((sum, btn, i) => sum + btn.offsetWidth + (i > 0 ? GAP : 0), 0);

      if (totalWidth <= availableForButtons) {
        this.renderer.setStyle(this.container, "overflow", "hidden");
        return;
      }

      this.setMoreButtonVisible(true);
      const moreButtonWidth = getOuterWidth(this.moreButton) || 160;
      this.setMoreButtonVisible(false);

      this.renderer.setStyle(this.container, "overflow", "hidden");

      const maxWidth = availableForButtons - moreButtonWidth;
      const visibleFlags = this.determineVisibleButtons(buttons, maxWidth);
      const hiddenButtons = buttons.filter((_, i) => !visibleFlags[i]);

      if (hiddenButtons.length > 0) {
        this.renderer.addClass(this.container, "is-overflowing");
        hiddenButtons.forEach((btn) => {
          this.renderer.addClass(btn, "sub-overflow-hidden");
          this.renderer.setStyle(btn, "display", "none");
        });
        this.setMoreButtonVisible(true);
        this.updateMenuContent(hiddenButtons);
      } else {
        this.closeMenu();
      }
    } finally {
      this.isCalculating = false;
    }
  }

  private measureReservedWidth(firstNavButton: HTMLElement): number {
    let left = PADDING;
    let el = this.container.firstElementChild as HTMLElement | null;
    while (el && el !== firstNavButton && el !== this.moreButton && !el.classList.contains("spacer")) {
      if (isVisible(el)) {
        left += getOuterWidth(el) + GAP;
      }
      el = el.nextElementSibling as HTMLElement | null;
    }

    let right = PADDING;
    const spacer = this.spacer;
    if (spacer) {
      let sibling = spacer.nextElementSibling as HTMLElement | null;
      while (sibling) {
        if (sibling !== this.moreButton && sibling !== this.menuContainer && isVisible(sibling)) {
          right += getOuterWidth(sibling) + GAP;
        }
        sibling = sibling.nextElementSibling as HTMLElement | null;
      }
    }

    return left + right;
  }

  private determineVisibleButtons(buttons: HTMLElement[], maxWidth: number): boolean[] {
    const visible = new Array(buttons.length).fill(false);
    let usedWidth = 0;
    const priorityIndices = new Set<number>();

    for (let i = 0; i < buttons.length; i++) {
      if (buttons[i].hasAttribute("data-overflow-pinned")) {
        const w = buttons[i].offsetWidth + GAP;
        if (usedWidth + w <= maxWidth) {
          usedWidth += w;
          visible[i] = true;
          priorityIndices.add(i);
        }
      }
    }

    const activeIndex = buttons.findIndex(isActive);
    if (activeIndex >= 0 && !priorityIndices.has(activeIndex)) {
      const w = buttons[activeIndex].offsetWidth + GAP;
      if (usedWidth + w <= maxWidth) {
        usedWidth += w;
        visible[activeIndex] = true;
        priorityIndices.add(activeIndex);
      }
      if (activeIndex > 0 && buttons[activeIndex].hasAttribute("data-overflow-child")) {
        const parentIndex = activeIndex - 1;
        if (!priorityIndices.has(parentIndex)) {
          const pw = buttons[parentIndex].offsetWidth + GAP;
          if (usedWidth + pw <= maxWidth) {
            usedWidth += pw;
            visible[parentIndex] = true;
            priorityIndices.add(parentIndex);
          }
        }
      }
    }

    for (let i = 0; i < buttons.length; i++) {
      if (priorityIndices.has(i)) continue;
      const w = buttons[i].offsetWidth + GAP;
      if (usedWidth + w <= maxWidth) {
        usedWidth += w;
        visible[i] = true;
      } else {
        break;
      }
    }

    return visible;
  }

  private setMoreButtonVisible(show: boolean): void {
    if (show) {
      this.renderer.removeClass(this.moreButton, "overflow-more-hidden");
    } else {
      this.renderer.addClass(this.moreButton, "overflow-more-hidden");
    }
  }

  private getNavButtons(): HTMLElement[] {
    const spacer = this.spacer;
    return (Array.from(this.container.children) as HTMLElement[]).filter(
      (el) =>
        el !== this.moreButton &&
        (el.tagName === "BUTTON" || el.tagName === "A") &&
        !el.classList.contains("overflow-more-btn") &&
        !el.closest(".spacer") &&
        (!spacer || !(spacer.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING))
    );
  }

  private updateMenuContent(hiddenButtons: HTMLElement[]): void {
    this.menuItemUnlisteners.forEach((fn) => fn());
    this.menuItemUnlisteners = [];
    this.menuContainer.innerHTML = "";

    for (const btn of hiddenButtons) {
      const menuItem = this.renderer.createElement("button");
      this.renderer.setAttribute(menuItem, "type", "button");
      this.renderer.setStyle(menuItem, "text-decoration", "none");
      this.renderer.addClass(menuItem, "overflow-menu-item");
      if (isActive(btn)) {
        this.renderer.addClass(menuItem, "overflow-menu-item-active");
      }

      const srcIcon = btn.querySelector("mat-icon");
      if (srcIcon) {
        const customClasses: string[] = [];
        srcIcon.classList.forEach((cls: string) => {
          if (cls.startsWith("ms--") || cls.startsWith("mdi--")) {
            customClasses.push(cls);
          }
        });
        this.renderer.appendChild(menuItem, this.createMatIcon(srcIcon.textContent?.trim() || "", customClasses));
      }

      const label = this.renderer.createElement("span");
      label.textContent = this.extractButtonText(btn);
      this.renderer.appendChild(menuItem, label);

      this.menuItemUnlisteners.push(
        this.renderer.listen(menuItem, "click", (e: Event) => {
          e.stopPropagation();
          btn.click();
          this.closeMenu();
        })
      );

      this.renderer.appendChild(this.menuContainer, menuItem);
    }
  }

  private extractButtonText(btn: HTMLElement): string {
    for (const span of Array.from(btn.querySelectorAll("span"))) {
      if (MAT_INTERNAL_SPANS.some((cls) => span.classList.contains(cls))) continue;
      const text = span.textContent?.trim();
      if (text) return text;
    }
    const labelSpan = btn.querySelector(".mdc-button__label");
    if (labelSpan) {
      const textParts: string[] = [];
      for (const node of Array.from(labelSpan.childNodes)) {
        if (node.nodeType === Node.TEXT_NODE) {
          const text = node.textContent?.trim();
          if (text) textParts.push(text);
        }
      }
      if (textParts.length > 0) return textParts.join(" ");
    }
    const directText: string[] = [];
    for (const node of Array.from(btn.childNodes)) {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent?.trim();
        if (text) directText.push(text);
      }
    }
    if (directText.length > 0) return directText.join(" ");
    return btn.textContent?.trim() || "";
  }

  private toggleMenu(): void {
    this.isMenuOpen ? this.closeMenu() : this.openMenu();
  }

  private openMenu(): void {
    const rect = this.moreButton.getBoundingClientRect();
    this.renderer.setStyle(this.menuContainer, "position", "fixed");
    this.renderer.setStyle(this.menuContainer, "top", `${rect.bottom + 4}px`);
    this.renderer.setStyle(this.menuContainer, "left", `${rect.left}px`);
    this.renderer.setStyle(this.menuContainer, "display", "block");
    this.isMenuOpen = true;
  }

  private closeMenu(): void {
    this.renderer.setStyle(this.menuContainer, "display", "none");
    this.isMenuOpen = false;
  }
}
