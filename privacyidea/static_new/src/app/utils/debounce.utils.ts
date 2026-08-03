/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { computed, signal, Signal, WritableSignal } from "@angular/core";

export const DEBOUNCE_MS = 300;

/**
 * Writes typed input to a signal only after the user stopped typing, while every
 * other change is applied at once.
 */
export class Debouncer<T> {
  /**
   * The value the user sees: the not yet applied input while typing, the applied
   * value otherwise. Read it wherever the input is displayed, so that the view
   * stays live during the delay.
   */
  readonly draft: Signal<T>;
  private timeoutId: ReturnType<typeof setTimeout> | undefined;
  private readonly pending = signal<{ value: T; base: T } | undefined>(undefined);

  constructor(
    private readonly target: WritableSignal<T>,
    private readonly delayMs: number = DEBOUNCE_MS
  ) {
    this.draft = computed(() => this.pending()?.value ?? this.target());
  }

  schedule(value: T): void {
    this.cancel();
    this.pending.set({ value, base: this.target() });
    this.timeoutId = setTimeout(() => this.commit(), this.delayMs);
  }

  set(value: T): void {
    this.cancel();
    this.target.set(value);
  }

  update(computeValue: (current: T) => T): void {
    this.set(computeValue(this.draft()));
  }

  cancel(): void {
    clearTimeout(this.timeoutId);
    this.timeoutId = undefined;
    this.pending.set(undefined);
  }

  private commit(): void {
    const pending = this.pending();
    this.timeoutId = undefined;
    this.pending.set(undefined);
    // Something else changed the value while the input was waiting - a route change
    // resetting it, or a write that bypassed this debouncer. Typed input based on the
    // superseded value must not win over that.
    if (!pending || this.target() !== pending.base) {
      return;
    }
    this.target.set(pending.value);
  }
}
