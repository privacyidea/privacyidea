/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { signal } from "@angular/core";

export class MockSessionTimerService {
  remainingTime = signal(300);
}
