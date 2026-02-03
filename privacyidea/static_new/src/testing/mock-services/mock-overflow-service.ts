/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { OverflowServiceInterface } from "../../app/services/overflow/overflow.service";

export class MockOverflowService implements OverflowServiceInterface {
  private _overflow = false;

  setWidthOverflow(value: boolean) {
    this._overflow = value;
  }

  isWidthOverflowing(_selector: string, _threshold: number): boolean {
    return this._overflow;
  }

  isHeightOverflowing(_args: { selector: string; threshold?: number; thresholdSelector?: string }): boolean {
    return this._overflow;
  }

  getOverflowThreshold(): number {
    return 1920;
  }
}
