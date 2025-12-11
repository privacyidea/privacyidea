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
import { inject, Injectable } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../content/content.service";

export interface OverflowServiceInterface {
  isWidthOverflowing(selector: string, threshold: number): boolean;

  isHeightOverflowing(params: { selector: string; threshold?: number; thresholdSelector?: string }): boolean;

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

  isHeightOverflowing(params: { selector: string; threshold?: number; thresholdSelector?: string }): boolean {
    const element = document.querySelector<HTMLElement>(params.selector);
    if (!element) return false;

    if (params.threshold !== undefined) {
      return element.clientHeight < params.threshold;
    }

    if (params.thresholdSelector) {
      const thresholdElement = document.querySelector<HTMLElement>(params.thresholdSelector);
      if (!thresholdElement) return false;

      const computedStyle = window.getComputedStyle(thresholdElement);
      const paddingBottom = parseFloat(computedStyle.paddingBottom) || 0;
      const threshold = thresholdElement.clientHeight - paddingBottom;
      return element.clientHeight < threshold;
    }

    return false;
  }

  getOverflowThreshold(): number {
    if (this.contentService.onTokenDetails()) return 1880;
    if (this.contentService.onTokensContainersDetails()) return 1880;
    if (this.contentService.onUserDetails()) return 1500;
    if (this.contentService.onTokens()) return 1880;
    if (this.contentService.onTokensContainers()) return 1880;
    if (this.contentService.onTokensChallenges()) return 1880;
    if (this.contentService.onUsers()) return 1880;
    if (this.contentService.onTokensApplications()) return 1500;
    if (this.contentService.onTokensEnrollment()) return 1240;
    if (this.contentService.onTokensContainersCreate()) return 1240;
    if (this.contentService.onTokensGetSerial()) return 1240;

    return 1920;
  }
}
