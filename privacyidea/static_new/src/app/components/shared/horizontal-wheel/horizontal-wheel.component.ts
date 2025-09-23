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
  Input
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
  @Input({ required: false }) values = signal<string[]>([
    "AAAAAAAAAAAA",
    "BBBBBBBBBBBB",
    "CCCCCCCCCCCC",
    "DDDDDDDDDDDD",
    "EEEEEEEEEEEE",
    "FFFFFFFFFFFF",
    "GGGGGGGGGGGG",
    "HHHHHHHHHHHH",
    "IIIIIIIIIIII",
    "JJJJJJJJJJJJ",
    "KKKKKKKKKKKK"
  ]);
  selectedValue = signal<string | null>(null);

  isDragging = false;
  startX = 0;
  scrollLeft = 0;

  private containerElement: HTMLElement | null = null;
  private items = viewChildren<ElementRef<HTMLElement>>("item");

  @Output() onSelect = new EventEmitter<string>();

  constructor(private elementRef: ElementRef) {}

  ngAfterViewInit(): void {
    this.containerElement = this.elementRef.nativeElement.querySelector(".wheel-container");
    if (this.containerElement) {
      this.containerElement.addEventListener("scroll", () => this.onScroll());
      this.setDynamicPadding();

      // Findet das Element in der Mitte und zentriert es beim Start.
      setTimeout(() => {
        this._transformItemsOnScroll();
        if (this.selectedValue()) {
          const selectedIndex = this.values().indexOf(this.selectedValue()!);
          if (selectedIndex !== -1) {
            this.centerElementByIndex(selectedIndex);
          }
        }
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
    if (!this.containerElement) return;
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
      this.onSelect.emit(this.values()[closestIndex]);
    }
  }

  onItemClick(e: MouseEvent, index: number) {
    e.preventDefault();
    this.centerElementByIndex(index);
  }

  private centerElementByIndex(index: number) {
    if (!this.containerElement || !this.items()) return;
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
      this.isDragging = false;

      // Findet das am nächsten liegende Element basierend auf der Scroll-Position
      const containerScrollLeft = this.containerElement!.scrollLeft;
      const containerMidpoint = containerScrollLeft + this.containerElement!.offsetWidth / 2;
      let closestIndex = -1;
      let minDistance = Infinity;

      this.items().forEach((itemRef, index) => {
        const itemElement = itemRef.nativeElement;
        const itemMidpoint = itemElement.offsetLeft + itemElement.offsetWidth / 2;
        const distance = Math.abs(containerMidpoint - itemMidpoint);

        if (distance < minDistance) {
          minDistance = distance;
          closestIndex = index;
        }
      });

      // Zentriert das am nächsten liegende Element
      if (closestIndex !== -1) {
        this.centerElementByIndex(closestIndex);
      }
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
