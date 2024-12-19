import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class OverflowService {
  isOverflowing(selector: string, threshold: number): boolean {
    const element = document.querySelector(selector);
    return element ? element.clientWidth < threshold : false;
  }

  isOverflowing1580(selector: string): boolean {
    return this.isOverflowing(selector, 1580);
  }

  isOverflowing1310(selector: string): boolean {
    return this.isOverflowing(selector, 1310);
  }

  isOverflowing1880(selector: string): boolean {
    return this.isOverflowing(selector, 1880);
  }
}
