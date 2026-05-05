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
import { Component, ElementRef, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { OverflowNavDirective } from "./overflow-nav.directive";

// ── Helpers ──────────────────────────────────────────────────────────────────

function mockElementWidth(el: HTMLElement, width: number): void {
  Object.defineProperty(el, "offsetWidth", { configurable: true, get: () => width });
}

function mockClientWidth(el: HTMLElement, width: number): void {
  Object.defineProperty(el, "clientWidth", { configurable: true, get: () => width });
}

const originalGetComputedStyle = window.getComputedStyle;

function patchGetComputedStyle(): void {
  window.getComputedStyle = (el: Element) => {
    const real = originalGetComputedStyle(el);
    return new Proxy(real, {
      get(target, prop) {
        if (prop === "display") return (el as HTMLElement).style?.display === "none" ? "none" : "block";
        if (prop === "visibility") return "visible";
        if (prop === "marginLeft" || prop === "marginRight") return "0";
        return Reflect.get(target, prop);
      }
    }) as CSSStyleDeclaration;
  };
}

function restoreGetComputedStyle(): void {
  window.getComputedStyle = originalGetComputedStyle;
}

/** Wait for the directive's setTimeout(50) to fire. */
function waitForInit(): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, 60));
}

// ── Test host components ─────────────────────────────────────────────────────

@Component({
  standalone: true,
  imports: [OverflowNavDirective],
  template: `
    <nav #nav appOverflowNav>
      <button class="nav-button" id="btn1"><mat-icon class="mat-icon material-icons">home</mat-icon><span>Home</span></button>
      <button class="nav-button" id="btn2"><mat-icon class="mat-icon material-icons">list</mat-icon><span>Tokens</span></button>
      <button class="nav-button" id="btn3"><mat-icon class="mat-icon material-icons">people</mat-icon><span>Users</span></button>
      <button class="nav-button" id="btn4"><mat-icon class="mat-icon material-icons">settings</mat-icon><span>Config</span></button>
      <div class="spacer"></div>
      <button class="nav-button" id="right1"><span>Profile</span></button>
    </nav>
  `
})
class TestHostComponent {
  @ViewChild("nav", { read: ElementRef }) navRef!: ElementRef<HTMLElement>;
}

@Component({
  standalone: true,
  imports: [OverflowNavDirective],
  template: `
    <nav #nav appOverflowNav>
      <div class="spacer"></div>
    </nav>
  `
})
class EmptyHostComponent {
  @ViewChild("nav", { read: ElementRef }) navRef!: ElementRef<HTMLElement>;
}

@Component({
  standalone: true,
  imports: [OverflowNavDirective],
  template: `
    <nav #nav appOverflowNav>
      <button class="nav-button" id="btn1"><span>Home</span></button>
      <button class="nav-button nav-active" id="btn2"><span>Tokens</span></button>
      <button class="nav-button" id="btn3"><span>Users</span></button>
      <div class="spacer"></div>
    </nav>
  `
})
class ActiveHostComponent {
  @ViewChild("nav", { read: ElementRef }) navRef!: ElementRef<HTMLElement>;
}

@Component({
  standalone: true,
  imports: [OverflowNavDirective],
  template: `
    <nav #nav appOverflowNav>
      <button class="nav-button" id="btn1"><span>Home</span></button>
      <button class="nav-button" id="btn2"><span>Tokens</span></button>
    </nav>
  `
})
class NoSpacerHostComponent {
  @ViewChild("nav", { read: ElementRef }) navRef!: ElementRef<HTMLElement>;
}

describe("OverflowNavDirective", () => {
  beforeAll(() => {
    patchGetComputedStyle();
  });

  afterAll(() => {
    restoreGetComputedStyle();
  });

  afterEach(() => {
    document.querySelectorAll(".overflow-dropdown").forEach(el => el.remove());
  });

  function setUpWidths(container: HTMLElement, containerWidth: number, buttonWidth: number): void {
    mockClientWidth(container, containerWidth);
    container.querySelectorAll("button.nav-button, a.nav-button").forEach(btn =>
      mockElementWidth(btn as HTMLElement, buttonWidth)
    );
    const spacer = container.querySelector(".spacer");
    if (spacer) mockElementWidth(spacer as HTMLElement, 0);
    const moreBtn = container.querySelector(".overflow-more-btn");
    if (moreBtn) mockElementWidth(moreBtn as HTMLElement, 80);
  }

  async function setup<T>(comp: new (...args: any[]) => T, containerWidth: number, buttonWidth: number) {
    const fixture = TestBed.createComponent(comp);
    fixture.detectChanges();
    await fixture.whenStable();

    const navRef = (fixture.componentInstance as any).navRef as ElementRef<HTMLElement>;
    const navEl = navRef.nativeElement;
    setUpWidths(navEl, containerWidth, buttonWidth);

    await waitForInit();
    fixture.detectChanges();

    return { fixture, navEl };
  }

  describe("creation", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should create a more button inside the container", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 2000, 100);
      expect(navEl.querySelector(".overflow-more-btn")).toBeTruthy();
      fixture.destroy();
    });

    it("should create a dropdown container in the document body", async () => {
      const { fixture } = await setup(TestHostComponent, 2000, 100);
      expect(document.querySelector(".overflow-dropdown")).toBeTruthy();
      fixture.destroy();
    });

    it("should insert more button before the spacer", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 2000, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      const spacer = navEl.querySelector(".spacer") as HTMLElement;
      expect(moreBtn.compareDocumentPosition(spacer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      fixture.destroy();
    });

    it("should have the correct classes on more button", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 2000, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      expect(moreBtn.classList.contains("nav-button")).toBe(true);
      expect(moreBtn.classList.contains("mdc-button")).toBe(true);
      expect(moreBtn.classList.contains("mat-mdc-button")).toBe(true);
      expect(moreBtn.getAttribute("type")).toBe("button");
      fixture.destroy();
    });

    it("should contain an icon with more_horiz text", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 2000, 100);
      const icon = navEl.querySelector(".overflow-more-btn mat-icon");
      expect(icon).toBeTruthy();
      expect(icon!.textContent).toBe("more_horiz");
      fixture.destroy();
    });

    it("should contain a label span with 'More' text", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 2000, 100);
      const span = navEl.querySelector(".overflow-more-btn span");
      expect(span).toBeTruthy();
      expect(span!.textContent).toBe("More");
      fixture.destroy();
    });
  });

  describe("no spacer", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [NoSpacerHostComponent]
      }).compileComponents();
    });

    it("should append more button at end when no spacer", async () => {
      const { navEl, fixture } = await setup(NoSpacerHostComponent, 2000, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      expect(navEl.lastElementChild).toBe(moreBtn);
      fixture.destroy();
    });
  });

  describe("overflow calculation", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should hide more button when all buttons fit", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 2000, 80);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      expect(moreBtn.classList.contains("overflow-more-hidden")).toBe(true);
      expect(navEl.classList.contains("is-overflowing")).toBe(false);
      expect(navEl.querySelectorAll(".sub-overflow-hidden").length).toBe(0);
      fixture.destroy();
    });

    it("should show more button and hide buttons when container is narrow", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 250, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      expect(moreBtn.classList.contains("overflow-more-hidden")).toBe(false);
      expect(navEl.querySelectorAll(".sub-overflow-hidden").length).toBeGreaterThan(0);
      expect(navEl.classList.contains("is-overflowing")).toBe(true);
      fixture.destroy();
    });

    it("should set hidden buttons to display:none", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 250, 100);
      const hidden = navEl.querySelectorAll(".sub-overflow-hidden");
      hidden.forEach(el => {
        expect((el as HTMLElement).style.display).toBe("none");
      });
      fixture.destroy();
    });

    it("should not include buttons after spacer in overflow menu", async () => {
      const { fixture } = await setup(TestHostComponent, 100, 100);
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      const menuTexts = Array.from(dropdown.querySelectorAll(".overflow-menu-item"))
        .map(el => el.textContent?.trim());
      expect(menuTexts).not.toContain("Profile");
      fixture.destroy();
    });
  });

  describe("empty nav", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [EmptyHostComponent]
      }).compileComponents();
    });

    it("should hide more button when there are no nav buttons", async () => {
      const { navEl, fixture } = await setup(EmptyHostComponent, 500, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      expect(moreBtn.classList.contains("overflow-more-hidden")).toBe(true);
      fixture.destroy();
    });
  });

  describe("active button prioritization", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [ActiveHostComponent]
      }).compileComponents();
    });

    it("should keep the active button visible when space is limited", async () => {
      const { navEl, fixture } = await setup(ActiveHostComponent, 350, 100);
      const btn2 = navEl.querySelector("#btn2") as HTMLElement;
      // The active button should be prioritized and remain visible
      expect(btn2.classList.contains("sub-overflow-hidden")).toBe(false);
      fixture.destroy();
    });
  });

  describe("dropdown menu", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should populate dropdown with hidden button labels", async () => {
      const { fixture } = await setup(TestHostComponent, 200, 100);
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      const items = dropdown.querySelectorAll(".overflow-menu-item");
      expect(items.length).toBeGreaterThan(0);
      items.forEach(item => {
        const span = item.querySelector("span");
        expect(span).toBeTruthy();
        expect(span!.textContent!.trim().length).toBeGreaterThan(0);
      });
      fixture.destroy();
    });

    it("should copy icons to menu items", async () => {
      const { fixture } = await setup(TestHostComponent, 200, 100);
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      const items = dropdown.querySelectorAll(".overflow-menu-item");
      items.forEach(item => {
        const icon = item.querySelector("mat-icon");
        expect(icon).toBeTruthy();
        expect(icon!.classList.contains("mat-icon")).toBe(true);
        expect(icon!.classList.contains("material-icons")).toBe(true);
      });
      fixture.destroy();
    });

    it("should open dropdown on more button click", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      moreBtn.click();
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      expect(dropdown.style.display).toBe("block");
      fixture.destroy();
    });

    it("should close dropdown on second click (toggle)", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      moreBtn.click();
      moreBtn.click();
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      expect(dropdown.style.display).toBe("none");
      fixture.destroy();
    });

    it("should close dropdown on document click", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      moreBtn.click();
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      expect(dropdown.style.display).toBe("block");
      document.dispatchEvent(new Event("click"));
      expect(dropdown.style.display).toBe("none");
      fixture.destroy();
    });

    it("should trigger original button click when menu item is clicked", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const hiddenBtn = navEl.querySelector(".sub-overflow-hidden") as HTMLElement;
      expect(hiddenBtn).toBeTruthy();

      const clickSpy = jest.fn();
      hiddenBtn.addEventListener("click", clickSpy);

      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      moreBtn.click();

      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      const firstItem = dropdown.querySelector(".overflow-menu-item") as HTMLElement;
      firstItem.click();

      expect(clickSpy).toHaveBeenCalled();
      expect(dropdown.style.display).toBe("none");
      fixture.destroy();
    });

    it("should open dropdown on Enter key", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      moreBtn.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      expect(dropdown.style.display).toBe("block");
      fixture.destroy();
    });

    it("should open dropdown on Space key", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      moreBtn.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      expect(dropdown.style.display).toBe("block");
      fixture.destroy();
    });
  });

  describe("dropdown positioning", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should position dropdown below the more button", async () => {
      const { navEl, fixture } = await setup(TestHostComponent, 200, 100);
      const moreBtn = navEl.querySelector(".overflow-more-btn") as HTMLElement;
      jest.spyOn(moreBtn, "getBoundingClientRect").mockReturnValue({
        top: 50, bottom: 90, left: 100, right: 180,
        width: 80, height: 40, x: 100, y: 50, toJSON: () => ({})
      });

      moreBtn.click();

      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      expect(dropdown.style.position).toBe("fixed");
      expect(dropdown.style.top).toBe("94px");
      expect(dropdown.style.left).toBe("100px");
      fixture.destroy();
    });
  });

  describe("active items in dropdown", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [ActiveHostComponent]
      }).compileComponents();
    });

    it("should mark active items in dropdown with overflow-menu-item-active", async () => {
      const { navEl, fixture } = await setup(ActiveHostComponent, 100, 100);
      const btn2 = navEl.querySelector("#btn2") as HTMLElement;
      if (btn2.classList.contains("sub-overflow-hidden")) {
        const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
        const activeItems = dropdown.querySelectorAll(".overflow-menu-item-active");
        expect(activeItems.length).toBe(1);
      }
      fixture.destroy();
    });
  });

  describe("custom icon classes", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should copy ms-- and mdi-- classes to menu item icons", async () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();
      await fixture.whenStable();

      const navEl = fixture.componentInstance.navRef.nativeElement;
      const btn1Icon = navEl.querySelector("#btn1 mat-icon") as HTMLElement;
      btn1Icon.classList.add("ms--custom-icon");
      btn1Icon.classList.add("mdi--other");

      setUpWidths(navEl, 100, 100);
      await waitForInit();
      fixture.detectChanges();

      const btn1 = navEl.querySelector("#btn1") as HTMLElement;
      if (btn1.classList.contains("sub-overflow-hidden")) {
        const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
        const menuIcons = Array.from(dropdown.querySelectorAll("mat-icon"));
        const matchingIcon = menuIcons.find(icon =>
          icon.classList.contains("ms--custom-icon") && icon.classList.contains("mdi--other")
        );
        expect(matchingIcon).toBeTruthy();
      }
      fixture.destroy();
    });
  });

  describe("text extraction", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should ignore mat-internal spans when extracting text", async () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();
      await fixture.whenStable();

      const navEl = fixture.componentInstance.navRef.nativeElement;
      const btn1 = navEl.querySelector("#btn1") as HTMLElement;
      const touchTarget = document.createElement("span");
      touchTarget.classList.add("mat-mdc-button-touch-target");
      touchTarget.textContent = "IGNORE";
      btn1.appendChild(touchTarget);

      setUpWidths(navEl, 100, 100);
      await waitForInit();
      fixture.detectChanges();

      const dropdown = document.querySelector(".overflow-dropdown") as HTMLElement;
      const items = dropdown.querySelectorAll(".overflow-menu-item");
      items.forEach(item => {
        expect(item.textContent).not.toContain("IGNORE");
      });
      fixture.destroy();
    });
  });

  describe("cleanup", () => {
    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [TestHostComponent]
      }).compileComponents();
    });

    it("should remove dropdown from body on destroy", async () => {
      const { fixture } = await setup(TestHostComponent, 2000, 100);
      expect(document.querySelector(".overflow-dropdown")).toBeTruthy();
      fixture.destroy();
      expect(document.querySelector(".overflow-dropdown")).toBeFalsy();
    });

    it("should not throw on destroy", async () => {
      const { fixture } = await setup(TestHostComponent, 2000, 100);
      expect(() => fixture.destroy()).not.toThrow();
    });
  });
});


