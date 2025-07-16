import { Injectable } from '@angular/core';

export interface OverflowServiceInterface {
  isWidthOverflowing(selector: string, threshold: number): boolean;
  isHeightOverflowing(params: {
    selector: string;
    threshold?: number;
    thresholdSelector?: string;
  }): boolean;
  getOverflowThreshold(selectedContent: string): number;
}

@Injectable({
  providedIn: 'root',
})
export class OverflowService implements OverflowServiceInterface {
  isWidthOverflowing(selector: string, threshold: number): boolean {
    const element = document.querySelector(selector);
    return element ? element.clientWidth < threshold : false;
  }

  isHeightOverflowing(params: {
    selector: string;
    threshold?: number;
    thresholdSelector?: string;
  }): boolean {
    const element = document.querySelector<HTMLElement>(params.selector);
    if (!element) return false;

    if (params.threshold !== undefined) {
      return element.clientHeight < params.threshold;
    } else if (params.thresholdSelector) {
      const thresholdElement = document.querySelector<HTMLElement>(
        params.thresholdSelector,
      );
      if (!thresholdElement) return false;
      const computedStyle = window.getComputedStyle(thresholdElement);
      const paddingBottom = parseFloat(computedStyle.paddingBottom) || 0;
      const thresholdHeightWithoutPadding =
        thresholdElement.clientHeight - paddingBottom;
      return element.clientHeight < thresholdHeightWithoutPadding + 150;
    } else {
      return false;
    }
  }

  getOverflowThreshold(selectedContent: string): number {
    switch (selectedContent) {
      case 'token_details':
        return 1880;
      case 'container_details':
        return 1880;
      case 'token_overview':
        return 1880;
      case 'container_overview':
        return 1880;
      case 'token_challenges':
        return 1880;
      case 'token_applications':
        return 1500;
      case 'token_enrollment':
        return 1240;
      case 'container_create':
        return 1240;
      case 'token_get_serial':
        return 1240;
    }
    return 1920;
  }
}
