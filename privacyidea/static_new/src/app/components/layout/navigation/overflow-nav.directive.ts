/**
 * Directive that detects overflow in a flex container and moves overflowing
 * buttons into a "More" menu. Applied to a container element (e.g. mat-toolbar).
 *
 * Usage:
 *   <mat-toolbar class="secondary-toolbar" appOverflowNav>
 *     ... buttons ...
 *   </mat-toolbar>
 *
 * The directive will:
 * 1. Observe the container for resize
 * 2. Hide buttons that don't fit with a CSS class
 * 3. Show a "More" button with a mat-menu containing the hidden items
 */
import {
  Directive,
  ElementRef,
  AfterViewInit,
  OnDestroy,
  NgZone,
  inject,
  Renderer2
} from "@angular/core";

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

  ngAfterViewInit(): void {
    this.createMoreButton();
    this.setupObservers();
    // Initial calculation after render
    setTimeout(() => this.calculateOverflow(), 50);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.mutationObserver?.disconnect();
    this.removeMenu();
  }

  private createMoreButton(): void {
    const container = this.el.nativeElement;

    // Create the "More" button — matches the primary nav's mat-button style
    this.moreButton = this.renderer.createElement("button");
    this.renderer.addClass(this.moreButton, "overflow-more-btn");
    this.renderer.addClass(this.moreButton, "nav-button");
    this.renderer.addClass(this.moreButton, "mdc-button");
    this.renderer.addClass(this.moreButton, "mat-mdc-button");

    const icon = this.renderer.createElement("span");
    this.renderer.addClass(icon, "material-icons");
    icon.textContent = "more_horiz";
    this.renderer.appendChild(this.moreButton, icon);

    const label = this.renderer.createElement("span");
    label.textContent = "More";
    this.renderer.appendChild(this.moreButton, label);
    this.renderer.addClass(this.moreButton, "overflow-more-hidden");
    this.renderer.setStyle(this.moreButton, "flex-shrink", "0");

    // Create dropdown container
    this.menuContainer = this.renderer.createElement("div");
    this.renderer.addClass(this.menuContainer, "overflow-dropdown");
    this.renderer.setStyle(this.menuContainer, "display", "none");

    this.renderer.listen(this.moreButton, "click", (e: Event) => {
      e.stopPropagation();
      this.toggleMenu();
    });

    // Close on outside click
    this.renderer.listen("document", "click", () => {
      if (this.isMenuOpen) {
        this.closeMenu();
      }
    });

    // Insert before the spacer or at end
    const spacer = container.querySelector(".spacer");
    if (spacer) {
      this.renderer.insertBefore(container, this.moreButton, spacer);
    } else {
      this.renderer.appendChild(container, this.moreButton);
    }

    // Append dropdown to body for proper layering
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

    // Watch for DOM changes (conditional buttons appearing/disappearing)
    // Only react to childList changes on the container itself, not subtree attribute changes
    this.mutationObserver = new MutationObserver((mutations) => {
      if (this.isCalculating) return;
      // Only recalculate if actual child nodes were added/removed (not our own style/class changes)
      const hasRelevantChange = mutations.some(m =>
        m.type === "childList" && (m.addedNodes.length > 0 || m.removedNodes.length > 0)
      );
      if (hasRelevantChange) {
        this.ngZone.run(() => this.calculateOverflow());
      }
    });
    this.mutationObserver.observe(container, { childList: true });
  }

  private calculateOverflow(): void {
    if (this.isCalculating) return;
    this.isCalculating = true;

    try {
      const container = this.el.nativeElement;
      const buttons = this.getNavButtons();

      if (buttons.length === 0) {
        this.renderer.addClass(this.moreButton, "overflow-more-hidden");
        this.closeMenu();
        return;
      }

    // First, show all buttons to measure
    buttons.forEach(btn => {
      this.renderer.removeStyle(btn, "display");
      this.renderer.removeClass(btn, "sub-overflow-hidden");
    });
    this.renderer.addClass(this.moreButton, "overflow-more-hidden");

    const containerWidth = container.clientWidth;

    // Measure the right-side elements (spacer + support/docs buttons + footer text)
    let rightWidth = 0;
    const spacer = container.querySelector(".spacer");
    if (spacer) {
      // Measure everything after the spacer
      let el = spacer.nextElementSibling;
      while (el) {
        if (el !== this.moreButton && el !== this.menuContainer) {
          rightWidth += (el as HTMLElement).offsetWidth + 4;
        }
        el = el.nextElementSibling;
      }
    }

    // Also account for footer text at the beginning
    const footerText = container.querySelector(".footer-text");
    let leftReserved = 0;
    if (footerText) {
      leftReserved = (footerText as HTMLElement).offsetWidth + 16;
    }

    const moreButtonWidth = 72;
    const gap = 4;
    const availableForButtons = containerWidth - leftReserved - rightWidth - 32; // 32 for padding

    let usedWidth = 0;
    let overflowStartIndex = buttons.length;

    for (let i = 0; i < buttons.length; i++) {
      const btnWidth = buttons[i].offsetWidth + gap;
      const remaining = buttons.length - i;
      const needsMore = remaining > 1;
      const maxWidth = needsMore ? availableForButtons - moreButtonWidth : availableForButtons;

      if (usedWidth + btnWidth <= maxWidth) {
        usedWidth += btnWidth;
      } else {
        overflowStartIndex = i;
        break;
      }
    }

    if (overflowStartIndex < buttons.length) {
      // Hide overflow buttons
      for (let i = overflowStartIndex; i < buttons.length; i++) {
        this.renderer.addClass(buttons[i], "sub-overflow-hidden");
        this.renderer.setStyle(buttons[i], "display", "none");
      }
      // Show More button
      this.renderer.removeClass(this.moreButton, "overflow-more-hidden");
      this.updateMenuContent(buttons.slice(overflowStartIndex));
    } else {
      this.renderer.addClass(this.moreButton, "overflow-more-hidden");
      this.closeMenu();
    }

    // Check if More button has an active item
    const hasActiveOverflow = buttons.slice(overflowStartIndex).some(
      btn => btn.classList.contains("sub-nav-active")
    );
    if (hasActiveOverflow) {
      this.renderer.addClass(this.moreButton, "nav-active");
    } else {
      this.renderer.removeClass(this.moreButton, "nav-active");
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
      el.tagName === "BUTTON" &&
      !el.classList.contains("overflow-more-btn") &&
      !el.closest(".spacer") &&
      // Exclude right-side buttons (after spacer)
      !this.isAfterSpacer(el)
    );
  }

  private isAfterSpacer(el: HTMLElement): boolean {
    const container = this.el.nativeElement;
    const spacer = container.querySelector(".spacer");
    if (!spacer) return false;
    // Compare DOM position
    return !!(spacer.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING);
  }

  private updateMenuContent(hiddenButtons: HTMLElement[]): void {
    if (!this.menuContainer) return;
    this.menuContainer.innerHTML = "";

    hiddenButtons.forEach(btn => {
      const menuItem = this.renderer.createElement("button");
      this.renderer.addClass(menuItem, "overflow-menu-item");
      if (btn.classList.contains("sub-nav-active")) {
        this.renderer.addClass(menuItem, "overflow-menu-item-active");
      }

      // Extract icon name from mat-icon element and render as material-icons span
      const icon = btn.querySelector("mat-icon");
      if (icon) {
        const iconSpan = this.renderer.createElement("span");
        this.renderer.addClass(iconSpan, "material-icons");
        iconSpan.textContent = icon.textContent?.trim() || "";
        // Copy any custom icon classes (e.g. ms--shield-list, mdi--folder-list)
        icon.classList.forEach((cls: string) => {
          if (cls.startsWith("ms--") || cls.startsWith("mdi--")) {
            this.renderer.addClass(iconSpan, cls);
          }
        });
        this.renderer.appendChild(menuItem, iconSpan);
      }

      // Extract text label
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
      // Fallback to button's own text
      if (!textContent) {
        textContent = btn.textContent?.trim() || "";
      }

      const label = this.renderer.createElement("span");
      label.textContent = textContent;
      this.renderer.appendChild(menuItem, label);

      this.renderer.listen(menuItem, "click", (e: Event) => {
        e.stopPropagation();
        btn.click();
        this.closeMenu();
      });

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

    // Position dropdown below the More button
    const rect = this.moreButton.getBoundingClientRect();
    this.renderer.setStyle(this.menuContainer, "position", "fixed");
    this.renderer.setStyle(this.menuContainer, "top", `${rect.bottom + 4}px`);
    this.renderer.setStyle(this.menuContainer, "left", `${rect.left}px`);
    this.renderer.setStyle(this.menuContainer, "display", "block");
    this.renderer.setStyle(this.menuContainer, "z-index", "1000");
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



