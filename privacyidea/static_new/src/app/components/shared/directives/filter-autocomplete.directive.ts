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
import { AfterViewInit, Directive, ElementRef, HostListener, inject, input, OnDestroy } from "@angular/core";

const SEPARATOR = /[^\s,]*$/;

export function filterKeywordCompletion(value: string, cursor: number, keywords: string[]): string {
  const token = SEPARATOR.exec(value.slice(0, cursor))?.[0] ?? "";
  if (!token || token.includes(":")) {
    return "";
  }
  const lower = token.toLowerCase();
  if (keywords.some((keyword) => keyword.toLowerCase() === lower)) {
    return ": ";
  }
  const matches = keywords.filter((keyword) => keyword.toLowerCase().startsWith(lower));
  if (matches.length === 0) {
    return "";
  }
  const best = matches.reduce((shortest, keyword) => (keyword.length < shortest.length ? keyword : shortest));
  return `${best.slice(token.length)}: `;
}

@Directive({
  selector: "[appFilterAutocomplete]",
  standalone: true
})
export class FilterAutocompleteDirective implements AfterViewInit, OnDestroy {
  readonly keywords = input<string[]>([], { alias: "appFilterAutocomplete" });

  private readonly input = inject<ElementRef<HTMLInputElement>>(ElementRef).nativeElement;
  private ghost?: HTMLElement;
  private content?: HTMLElement;
  private prefix?: HTMLElement;
  private suffix?: HTMLElement;
  private dismissed = false;
  private completion = "";

  ngAfterViewInit(): void {
    const parent = this.input.parentElement;
    if (!parent) {
      return;
    }
    if (getComputedStyle(parent).position === "static") {
      parent.style.position = "relative";
    }
    const ghost = document.createElement("div");
    ghost.className = "filter-autocomplete-ghost";
    ghost.setAttribute("aria-hidden", "true");
    this.content = document.createElement("span");
    this.content.className = "filter-autocomplete-content";
    this.prefix = document.createElement("span");
    this.prefix.className = "filter-autocomplete-prefix";
    this.suffix = document.createElement("span");
    this.suffix.className = "filter-autocomplete-suffix";
    this.content.append(this.prefix, this.suffix);
    ghost.appendChild(this.content);
    parent.appendChild(ghost);
    this.ghost = ghost;
    window.addEventListener("resize", this.update);
  }

  ngOnDestroy(): void {
    window.removeEventListener("resize", this.update);
    this.ghost?.remove();
  }

  @HostListener("input")
  @HostListener("click")
  @HostListener("focus")
  @HostListener("scroll")
  @HostListener("keyup")
  onInteraction(): void {
    this.dismissed = false;
    this.update();
  }

  @HostListener("blur")
  onBlur(): void {
    this.hide();
  }

  @HostListener("keydown", ["$event"])
  onKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape" && this.completion) {
      this.dismissed = true;
      this.hide();
      return;
    }
    if (event.key !== "Tab" || event.shiftKey || !this.completion) {
      return;
    }
    event.preventDefault();
    const cursor = this.input.selectionStart ?? this.input.value.length;
    const value = this.input.value.slice(0, cursor) + this.completion + this.input.value.slice(cursor);
    const caret = cursor + this.completion.length;
    this.input.value = value;
    this.input.setSelectionRange(caret, caret);
    this.input.dispatchEvent(new Event("input", { bubbles: true }));
    this.update();
  }

  private readonly update = (): void => {
    if (!this.ghost || !this.content || !this.prefix || !this.suffix) {
      return;
    }
    const value = this.input.value;
    const cursor = this.input.selectionStart ?? value.length;
    const collapsed = cursor === this.input.selectionEnd;
    const atEnd = cursor === value.length;
    const focused = document.activeElement === this.input;

    this.completion =
      focused && collapsed && atEnd && !this.dismissed ? filterKeywordCompletion(value, cursor, this.keywords()) : "";

    if (!this.completion) {
      this.hide();
      return;
    }

    const style = getComputedStyle(this.input);
    this.ghost.style.left = `${this.input.offsetLeft}px`;
    this.ghost.style.top = `${this.input.offsetTop}px`;
    this.ghost.style.width = `${this.input.offsetWidth}px`;
    this.ghost.style.height = `${this.input.offsetHeight}px`;
    this.ghost.style.font = style.font;
    this.ghost.style.letterSpacing = style.letterSpacing;
    this.ghost.style.paddingLeft = style.paddingLeft;
    this.ghost.style.paddingRight = style.paddingRight;
    this.ghost.style.borderLeft = `${style.borderLeftWidth} solid transparent`;
    this.ghost.style.borderRight = `${style.borderRightWidth} solid transparent`;
    this.content.style.transform = `translateX(-${this.input.scrollLeft}px)`;
    this.prefix.textContent = value;
    this.suffix.textContent = this.completion;
    this.ghost.style.display = "flex";
  };

  private hide(): void {
    this.completion = "";
    if (this.ghost) {
      this.ghost.style.display = "none";
    }
  }
}
