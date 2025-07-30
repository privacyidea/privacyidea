import { inject, Injectable } from '@angular/core';
import { ContentService } from '../content/content.service';

export interface OverflowServiceInterface {
  isWidthOverflowing(selector: string, threshold: number): boolean;
  isHeightOverflowing(params: {
    selector: string;
    threshold?: number;
    thresholdSelector?: string;
  }): boolean;
  getOverflowThreshold(): number;
}

@Injectable({
  providedIn: 'root',
})
export class OverflowService implements OverflowServiceInterface {
  private contentService = inject(ContentService);
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

  getOverflowThreshold(): number {
    if (this.contentService.routeUrl().startsWith('/tokens/details')) {
      return 1880;
    }
    if (
      this.contentService.routeUrl().startsWith('/tokens/containers/details')
    ) {
      return 1880;
    }
    switch (this.contentService.routeUrl()) {
      case '/tokens':
        return 1880;
      case '/tokens/containers':
        return 1880;
      case '/tokens/challenges':
        return 1880;
      case '/users':
        return 1880;
      case '/tokens/applications':
        return 1500;
      case '/tokens/enroll':
        return 1240;
      case '/tokens/containers/create':
        return 1240;
      case '/tokens/get-serial':
        return 1240;
    }
    return 1920;
  }
}
