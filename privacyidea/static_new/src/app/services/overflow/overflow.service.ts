import { inject, Injectable } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { ROUTE_PATHS } from "../../app.routes";

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
  providedIn: "root"
})
export class OverflowService implements OverflowServiceInterface {
  private readonly contentService: ContentServiceInterface = inject(ContentService);

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
      const thresholdElement = document.querySelector<HTMLElement>(params.thresholdSelector);
      if (!thresholdElement) return false;
      const computedStyle = window.getComputedStyle(thresholdElement);
      const paddingBottom = parseFloat(computedStyle.paddingBottom) || 0;
      const thresholdHeightWithoutPadding = thresholdElement.clientHeight - paddingBottom;
      return element.clientHeight < thresholdHeightWithoutPadding + 150;
    } else {
      return false;
    }
  }

  getOverflowThreshold(): number {
    if (this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
      return 1880;
    }
    if (this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS)) {
      return 1880;
    }
    switch (this.contentService.routeUrl()) {
      case ROUTE_PATHS.TOKENS:
        return 1880;
      case ROUTE_PATHS.TOKENS_CONTAINERS:
        return 1880;
      case ROUTE_PATHS.TOKENS_CHALLENGES:
        return 1880;
      case ROUTE_PATHS.USERS:
        return 1880;
      case ROUTE_PATHS.TOKENS_APPLICATIONS:
        return 1500;
      case ROUTE_PATHS.TOKENS_ENROLLMENT:
        return 1240;
      case ROUTE_PATHS.TOKENS_CONTAINERS_CREATE:
        return 1240;
      case ROUTE_PATHS.TOKENS_GET_SERIAL:
        return 1240;
    }
    return 1920;
  }
}
