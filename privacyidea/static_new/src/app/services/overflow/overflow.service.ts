import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class OverflowService {
  isOverflowing(selector: string, threshold: number): boolean {
    const element = document.querySelector(selector);
    return element ? element.clientWidth < threshold : false;
  }
}
