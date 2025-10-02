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
  effect
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
  @Output() onSelect: EventEmitter<any> = new EventEmitter<any>();

  selectedValue: WritableSignal<any> = signal(null); // Please check the effect where this will get updated when values change.

  // // Linked signal will not work here. Computiton will not be called when values change.
  // selectedValue: WritableSignal<any> = linkedSignal({
  //   source: this.values,
  //   computation: (source, previous) => {
  //     console.info("Computing selectedValue from source:", source, "previous:", previous);
  //     if (source.length === 0 && !previous) return null;
  //     if (previous) return previous;
  //     return source[0];
  //   }
  // });

  @Input({ required: true })
  set initialValue(value: any) {
    console.info("Initial value set to:", value);
    this.selectedValue.set(value);
    console.info("Selected value initialized to:", this.selectedValue());
  }

  isDragging = false;
  startX = 0;
  scrollLeft = 0;

  private containerElement: HTMLElement | null = null;
  private items = viewChildren<ElementRef<HTMLElement>>("item");

  constructor(private elementRef: ElementRef) {
    effect(() => {
      this.onSelect.emit(this.selectedValue());
    });

    effect(
      () => {
        // Unfortunately, linkedSignal's computation does not run on source changes.
        // So we need to manually check for changes here and set the initial value if needed.
        // When there is a fix or improvement for linkedSignal, please remove this effect.

        const currentValues = this.values();
        console.info("Effect triggered: values changed.");
        console.info("Available source values:", currentValues);

        // Initialize selectedValue with the first item if currentValues exist and no value is set yet.
        if (currentValues.length > 0 && !this.selectedValue()) {
          console.info("Setting initial value from first item:", currentValues[0]);
          this.selectedValue.set(currentValues[0]);
        }
      },
      { allowSignalWrites: true }
    );

    effect(() => {
      this.items();
      this.selectedValue();
      console.info("Effect triggered: items or selectedValue changed.");

      // Only execute UI side-effects if view elements exist.
      if (this.items().length > 0) {
        this.setDynamicPadding();
        this.centerSelectedElement();
      }
    });
  }

  ngAfterViewInit(): void {
    this.containerElement = this.elementRef.nativeElement.querySelector(".wheel-container");
    if (this.containerElement) {
      this.containerElement.addEventListener("scroll", () => this.onScroll());
      this.setDynamicPadding();

      // Timeout to ensure view rendering and stability after initial setup.
      setTimeout(() => {
        const initialIndex = this.values().indexOf(this.selectedValue());
        if (initialIndex !== -1) {
          this.centerElementByIndex(initialIndex);
        }
        this._transformItemsOnScroll();
      }, 0);
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

    if (closestIndex !== -1 && this.values()[closestIndex] !== this.selectedValue()) {
      this.selectedValue.set(this.values()[closestIndex]);
    }
  }

  onItemClick(e: MouseEvent, index: number) {
    const walk = e.pageX - this.startX;
    // Check if a drag movement occurred to prevent click event.
    if (this.isDragging && Math.abs(walk) > 10) return;
    e.preventDefault();
    this.centerElementByIndex(index);
  }

  private centerElementByIndex(index: number) {
    // Check for container, items, and valid index before accessing nativeElement.
    if (!this.containerElement || !this.items() || index < 0 || index >= this.items().length) return;
    const itemElement = this.items()[index].nativeElement;

    const targetScrollLeft =
      itemElement.offsetLeft - this.containerElement.offsetWidth / 2 + itemElement.offsetWidth / 2;

    this.containerElement.scrollTo({
      left: targetScrollLeft,
      behavior: "smooth"
    });
  }

  private centerSelectedElement() {
    const index = this.values().indexOf(this.selectedValue());
    console.info("Centering selected element at index:", index, "with value:", this.selectedValue());

    // Check for valid index and item existence before accessing nativeElement.
    if (index === -1 || !this.containerElement || !this.items() || index >= this.items().length) return;

    const itemElement = this.items()[index].nativeElement;

    const targetScrollLeft =
      itemElement.offsetLeft - this.containerElement.offsetWidth / 2 + itemElement.offsetWidth / 2;

    this.containerElement.scrollTo({
      left: targetScrollLeft,
      behavior: "smooth"
    });
  }

  onMouseDown(e: MouseEvent) {
    this.isDragging = true;
    this.containerElement = e.currentTarget as HTMLElement;
    this.startX = e.pageX;
    this.scrollLeft = this.containerElement.scrollLeft;
  }

  @HostListener("window:mouseup", ["$event"])
  onMouseUp(e: MouseEvent) {
    if (this.isDragging) {
      // Delay isDragging false to prevent click event after dragging.
      setTimeout(() => {
        this.isDragging = false;
      }, 100);

      this.centerSelectedElement();
    }
  }

  @HostListener("window:mousemove", ["$event"])
  onMouseMove(e: MouseEvent) {
    if (!this.isDragging || !this.containerElement) return;
    e.preventDefault();
    const walk = e.pageX - this.startX;
    this.containerElement.scrollLeft = this.scrollLeft - walk;
  }
}
