// src/app/shared/directives/scroll-adjuster.directive.ts
import {
  AfterViewInit,
  Directive,
  ElementRef,
  Input,
  NgZone,
  OnDestroy,
} from '@angular/core';
import { Subject } from 'rxjs'; // fromEvent and debounceTime are not directly used in the directive, but for context if you add back window resize listener.
// For current implementation, they are not needed here if ResizeObserver handles container resize.

@Directive({
  selector: '[appScrollAdjuster]',
  standalone: true,
})
export class ScrollAdjusterDirective implements AfterViewInit, OnDestroy {
  @Input() scrollItemSelector: string = '.scroll-item'; // Default selector, can be overridden

  private destroy$ = new Subject<void>();
  private resizeObserver!: ResizeObserver;
  private mutationObserver!: MutationObserver;

  constructor(
    private el: ElementRef<HTMLElement>,
    private ngZone: NgZone,
  ) {}

  ngAfterViewInit(): void {
    const container = this.el.nativeElement;

    const computedStyle = getComputedStyle(container);
    if (
      computedStyle.overflowY !== 'scroll' &&
      computedStyle.overflowY !== 'auto'
    ) {
      console.warn(
        'ScrollAdjusterDirective: Element must have overflow-y: scroll or auto.',
        container,
      );
    }

    this.resizeObserver = new ResizeObserver(() => {
      this.ngZone.runOutsideAngular(() => {
        this.adjustPadding();
      });
    });
    this.resizeObserver.observe(container);

    this.mutationObserver = new MutationObserver(() => {
      this.ngZone.runOutsideAngular(() => {
        this.adjustPadding();
      });
    });
    this.mutationObserver.observe(container, {
      childList: true,
      subtree: true,
    });

    this.ngZone.runOutsideAngular(() => {
      this.adjustPadding();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    if (this.mutationObserver) {
      this.mutationObserver.disconnect();
    }
  }

  private adjustPadding(): void {
    const container = this.el.nativeElement;
    const items = container.querySelectorAll(this.scrollItemSelector);
    if (!items || items.length === 0) {
      container.style.paddingTop = '0px';
      container.style.paddingBottom = '0px';
      return;
    }

    const containerHeight = container.clientHeight;
    const firstItem = items[0] as HTMLElement;
    const computedStyle = window.getComputedStyle(firstItem);
    const paddingTop = parseFloat(computedStyle.paddingTop);
    const paddingBottom = parseFloat(computedStyle.paddingBottom);
    const itemHeight = firstItem.clientHeight - paddingTop - paddingBottom;

    if (containerHeight === 0 || itemHeight === 0) {
      container.style.paddingTop = '0px';
      container.style.paddingBottom = '0px';
      return;
    }

    const effectivePadding = Math.max(0, itemHeight - containerHeight);
    firstItem.style.paddingTop = `${effectivePadding}px`;
    firstItem.style.paddingBottom = '0px';
  }
}
