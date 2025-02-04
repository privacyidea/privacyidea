import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class OverflowService {
  isWidthOverflowing(selector: string, threshold: number): boolean {
    const element = document.querySelector(selector);
    return element ? element.clientWidth < threshold : false;
  }

  isHeightOverflowing(selector: string, threshold: number): boolean {
    const element = document.querySelector(selector);
    return element ? element.clientHeight < threshold : false;
  }

  getOverflowThreshold(selectedContent: string) {
    switch (selectedContent) {
      case 'token_details':
        return 1880;
      case 'container_details':
        return 1880;
      case 'token_overview':
        return 1880;
      case 'container_overview':
        return 1880;
      case 'token_enrollment':
        return 1240;
      case 'token_get_serial':
        return 1240;
    }
    return 1920;
  }
}
