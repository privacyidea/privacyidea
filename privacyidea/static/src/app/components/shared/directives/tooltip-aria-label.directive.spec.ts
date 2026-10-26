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

import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { TooltipAriaLabelDirective } from "./tooltip-aria-label.directive";

@Component({
  standalone: true,
  imports: [MatIcon, MatTooltip, TooltipAriaLabelDirective],
  template: `
    <button
      id="icon"
      [matTooltip]="tip()"
      ><mat-icon aria-hidden="true">refresh</mat-icon></button
    >
    <button
      id="text"
      matTooltip="Tip"
      >Visible text</button
    >
    <button
      id="labelled"
      aria-label="Own name"
      matTooltip="Tip"
      ><mat-icon aria-hidden="true">x</mat-icon></button
    >
    <button
      id="labelledby"
      aria-labelledby="other"
      matTooltip="Tip"
      ><mat-icon aria-hidden="true">x</mat-icon></button
    >
    <a
      id="link"
      href="/x"
      matTooltip="Go"
      ><mat-icon aria-hidden="true">x</mat-icon></a
    >
    <span
      id="span"
      matTooltip="Not a control"></span>
    <button
      id="empty"
      matTooltip=""
      ><mat-icon aria-hidden="true">x</mat-icon></button
    >
    <button
      id="bound"
      [attr.aria-label]="boundLabel()"
      matTooltip="Tip"
      ><mat-icon aria-hidden="true">x</mat-icon></button
    >
    <button
      id="boundby"
      [attr.aria-labelledby]="boundLabelledBy()"
      matTooltip="Tip"
      ><mat-icon aria-hidden="true">x</mat-icon></button
    >
    <button
      id="conditional"
      matTooltip="Create"
      ><mat-icon aria-hidden="true">add</mat-icon>
      @if (showText()) {
        <span>Create item</span>
      }
    </button>
  `
})
class HostComponent {
  tip = signal("Refresh Resources");
  boundLabel = signal<string | null>(null);
  boundLabelledBy = signal<string | null>(null);
  showText = signal(false);
}

// jest.setup.ts replaces MutationObserver by an inert mock. This stand-in keeps the callback and the observed
// target, so a spec delivers the "DOM changed" notification itself, after it has changed the DOM.
class RecordingMutationObserver {
  static instances: RecordingMutationObserver[] = [];
  target?: Node;
  options?: MutationObserverInit;
  disconnected = false;

  constructor(private readonly callback: () => void) {
    RecordingMutationObserver.instances.push(this);
  }

  observe(target: Node, options: MutationObserverInit): void {
    this.target = target;
    this.options = options;
  }

  disconnect(): void {
    this.disconnected = true;
  }

  takeRecords(): MutationRecord[] {
    return [];
  }

  notify(): void {
    if (!this.disconnected) {
      this.callback();
    }
  }
}

describe("TooltipAriaLabelDirective", () => {
  const mockedMutationObserver = globalThis.MutationObserver;
  let fixture: ComponentFixture<HostComponent>;
  const el = (id: string): HTMLElement => fixture.debugElement.query(By.css("#" + id)).nativeElement;

  beforeEach(() => {
    RecordingMutationObserver.instances = [];
    globalThis.MutationObserver = RecordingMutationObserver as unknown as typeof MutationObserver;
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    globalThis.MutationObserver = mockedMutationObserver;
  });

  const observerOf = (id: string): RecordingMutationObserver =>
    RecordingMutationObserver.instances.find((observer) => observer.target === el(id))!;

  // Renders pending changes, then delivers the observers' notifications as the browser would.
  const settle = (): void => {
    fixture.detectChanges();
    RecordingMutationObserver.instances.forEach((observer) => observer.notify());
  };

  it("names an icon-only button with its tooltip", () => {
    expect(el("icon").getAttribute("aria-label")).toBe("Refresh Resources");
  });

  it("follows the tooltip when it changes", () => {
    fixture.componentInstance.tip.set("Reload");
    fixture.detectChanges();

    expect(el("icon").getAttribute("aria-label")).toBe("Reload");
  });

  it("names an icon-only link", () => {
    expect(el("link").getAttribute("aria-label")).toBe("Go");
  });

  it("leaves a button with visible text alone", () => {
    expect(el("text").hasAttribute("aria-label")).toBe(false);
  });

  it("keeps an aria-label the element sets itself", () => {
    expect(el("labelled").getAttribute("aria-label")).toBe("Own name");
  });

  it("keeps an aria-labelledby the element sets itself", () => {
    expect(el("labelledby").hasAttribute("aria-label")).toBe(false);
  });

  it("does not touch elements that are not buttons or links", () => {
    expect(el("span").hasAttribute("aria-label")).toBe(false);
  });

  it("sets no label for an empty tooltip", () => {
    expect(el("empty").hasAttribute("aria-label")).toBe(false);
  });

  it("names an element whose own aria-label binding is still null", () => {
    expect(el("bound").getAttribute("aria-label")).toBe("Tip");
  });

  it("steps back when another writer sets an aria-label later", () => {
    fixture.componentInstance.boundLabel.set("Own name");
    settle();

    expect(el("bound").getAttribute("aria-label")).toBe("Own name");
  });

  it("does not overwrite a later aria-label when the tooltip changes", () => {
    const button = el("icon");
    button.setAttribute("aria-label", "Written elsewhere");
    settle();
    fixture.componentInstance.tip.set("Reload");
    settle();

    expect(button.getAttribute("aria-label")).toBe("Written elsewhere");
  });

  it("names the element again when the other writer removes its aria-label", () => {
    fixture.componentInstance.boundLabel.set("Own name");
    settle();
    fixture.componentInstance.boundLabel.set(null);
    settle();

    expect(el("bound").getAttribute("aria-label")).toBe("Tip");
  });

  it("steps back when an aria-labelledby appears later and keeps it free of its own label", () => {
    fixture.componentInstance.boundLabelledBy.set("other");
    settle();

    expect(el("boundby").hasAttribute("aria-label")).toBe(false);
  });

  it("removes its label when visible text appears later", () => {
    expect(el("conditional").getAttribute("aria-label")).toBe("Create");

    fixture.componentInstance.showText.set(true);
    settle();

    expect(el("conditional").hasAttribute("aria-label")).toBe(false);
  });

  it("applies its label again when the visible text disappears", () => {
    fixture.componentInstance.showText.set(true);
    settle();
    fixture.componentInstance.showText.set(false);
    settle();

    expect(el("conditional").getAttribute("aria-label")).toBe("Create");
  });

  it("removes its label when a hidden child becomes readable", () => {
    const icon = el("icon").querySelector("mat-icon") as HTMLElement;
    icon.setAttribute("aria-hidden", "false");
    settle();

    expect(el("icon").hasAttribute("aria-label")).toBe(false);
  });

  it("does not remove an aria-label it did not write when visible text appears", () => {
    fixture.componentInstance.boundLabel.set("Own name");
    settle();
    el("bound").appendChild(document.createTextNode("Visible"));
    settle();

    expect(el("bound").getAttribute("aria-label")).toBe("Own name");
  });

  it("observes its host for text, aria-hidden and naming attributes", () => {
    expect(observerOf("icon").options).toEqual({
      childList: true,
      characterData: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["aria-label", "aria-labelledby", "aria-hidden"]
    });
  });

  it("disconnects its observer when destroyed", () => {
    const observer = observerOf("icon");
    fixture.destroy();

    expect(observer.disconnected).toBe(true);
  });
});
