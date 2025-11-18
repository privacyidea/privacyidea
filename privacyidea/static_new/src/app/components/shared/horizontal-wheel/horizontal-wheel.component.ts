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

import {
  Component,
  signal,
  ChangeDetectionStrategy,
  HostListener,
  Output,
  EventEmitter,
  ElementRef,
  AfterViewInit,
  viewChildren,
  Input,
  WritableSignal,
  Signal,
  effect,
  linkedSignal
} from "@angular/core";
import { CommonModule } from "@angular/common";

@Component({
  selector: "app-horizontal-wheel",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./horizontal-wheel.component.html",
  styleUrl: "./horizontal-wheel.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HorizontalWheelComponent implements AfterViewInit {
  @Input({ required: true }) values!: Signal<any[]>;
  @Input({ required: true }) initialValue!: any;
  @Output() onSelect: EventEmitter<string> = new EventEmitter<string>();

  // Linked signal will not work here. Computation will not be called when values change.
  selectedValue: WritableSignal<string> = linkedSignal<string[], string>({
    source: () => this.values(),
    computation: (source, previous) => {
      if (source.length === 0 && !previous) {
        return null;
      }
      if (previous?.value) {
        return previous.value;
      }
      return this.initialValue || source[0];
    }
  });

  isMouseDown = false;
  isDragging = false;
  startX = 0;
  scrollLeft = 0;

  private containerElement: HTMLElement | null = null;
  private items = viewChildren<ElementRef<HTMLElement>>("item");

  constructor(private elementRef: ElementRef) {
    effect(() => this.onSelect.emit(this.selectedValue()));

    effect(() => {
      this.items();
      this.selectedValue();

      // Only execute UI side-effects if view elements exist.
      if (this.items().length > 0) {
        this.setDynamicPadding();
        this._transformItemsOnScroll();
        this.centerSelectedElement();
      }
    });
  }

  ngAfterViewInit(): void {
    this.containerElement = this.elementRef.nativeElement.querySelector(".wheel-container");
    if (this.containerElement) {
      this.onScroll();
      this.containerElement.addEventListener("scroll", () => this.onScroll());
      this.setDynamicPadding();

      // Timeout to ensure view rendering and stability after initial setup.
      const initialIndex = this.values().indexOf(this.selectedValue());
      this.centerElementByIndex(initialIndex, { retrys: 3 }); // 3 retrys to ensure centering after potential layout shifts.
    }
  }

  @HostListener("window:resize", ["$event"])
  onResize() {
    this.setDynamicPadding();
    this._transformItemsOnScroll();
  }

  private setDynamicPadding() {
    if (!this.containerElement || !this.items() || this.items().length === 0) return;
    const itemWidth = this.items()[0].nativeElement.offsetWidth;
    this.containerElement.style.setProperty("--item-width", `${itemWidth}px`);
  }

  onScroll() {
    this._transformItemsOnScroll();
  }

  _transformItemsOnScroll() {
    if (!this.containerElement || this.items().length === 0) return;
    const items = this.items();
    const containerRect = this.containerElement.getBoundingClientRect();
    const containerMidpointX = containerRect.left + containerRect.width / 2;
    const containerWidth = containerRect.width;
    let closestIndex = -1;
    let minDistance = Infinity;

    items.forEach((itemRef, index) => {
      const itemElement = itemRef.nativeElement;
      const itemRect = itemElement.getBoundingClientRect();
      const itemMidpointX = itemRect.left + itemRect.width / 2;
      const distance = Math.abs(containerMidpointX - itemMidpointX);

      const maxDistance = containerWidth / 2;
      const normalizedDistance = Math.min(1, distance / maxDistance);

      const easedDistance = normalizedDistance * normalizedDistance;
      const maxAngle = 40;
      const angle = maxAngle * easedDistance;
      const rotateY = itemMidpointX < containerMidpointX ? -angle : angle;
      const scale = 1 - easedDistance * 0.3;
      const opacity = 1 - easedDistance * 0.7;

      const scaledWidth = itemRect.width * scale;
      const decresedWidthByRotation = Math.abs(Math.sin((rotateY * Math.PI) / 180)) * itemRect.width * 0.3;
      const effectiveWidth = scaledWidth - decresedWidthByRotation;
      const paddingAdjustment = (itemRect.width - effectiveWidth) / 2;

      itemElement.style.transform = `rotateY(${rotateY}deg) scale(${scale})`;
      itemElement.style.marginLeft = `-${paddingAdjustment}px`;
      itemElement.style.marginRight = `-${paddingAdjustment}px`;
      itemElement.style.opacity = `${opacity}`;

      if (distance < minDistance) {
        minDistance = distance;
        closestIndex = index;
      }
    });

    if (this.isDragging && closestIndex !== -1 && this.values()[closestIndex] !== this.selectedValue()) {
      this.selectedValue.set(this.values()[closestIndex]);
    }
  }

  onItemClick(e: MouseEvent, index: number) {
    const walk = e.pageX - this.startX;
    // Check if a drag movement occurred to prevent click event.
    if (this.isDragging) return;
    e.preventDefault();
    this.selectedValue.set(this.values()[index]);
    this.centerElementByIndex(index);
  }

  private centerElementByIndex(index: number, args: { retrys: number } = { retrys: 0 }) {
    let retrys = args.retrys;
    for (; retrys > -1; retrys--) {
      setTimeout(() => {
        // Check for valid index and item existence before accessing nativeElement.
        if (index === -1 || !this.containerElement || !this.items() || index >= this.items().length) return;

        const itemElement = this.items()[index].nativeElement;

        const targetScrollLeft =
          itemElement.offsetLeft - this.containerElement.offsetWidth / 2 + itemElement.offsetWidth / 2;
        this.containerElement.scrollTo({
          left: targetScrollLeft,
          behavior: "smooth"
        });
      }, retrys * 100);
    }
  }

  private centerSelectedElement() {
    const index = this.values().indexOf(this.selectedValue());
    this.centerElementByIndex(index);
  }

  onMouseDown(e: MouseEvent) {
    this.isMouseDown = true;
    this.containerElement = e.currentTarget as HTMLElement;
    this.startX = e.pageX;
    this.scrollLeft = this.containerElement.scrollLeft;
  }

  @HostListener("window:mouseup", ["$event"])
  onMouseUp(e: MouseEvent) {
    this.isMouseDown = false;
    if (this.isDragging) {
      // Delay isDragging false to prevent click event after dragging.
      setTimeout(() => {
        this.isDragging = false;
      }, 50);

      this.centerSelectedElement();
    }
  }

  @HostListener("window:mousemove", ["$event"])
  onMouseMove(e: MouseEvent) {
    const walk = e.pageX - this.startX;
    if (this.isMouseDown && Math.abs(walk) > 2) {
      this.isDragging = true;
    }
    if (!this.isDragging || !this.containerElement) return;
    e.preventDefault();
    this.containerElement.scrollLeft = this.scrollLeft - walk;
  }
}
