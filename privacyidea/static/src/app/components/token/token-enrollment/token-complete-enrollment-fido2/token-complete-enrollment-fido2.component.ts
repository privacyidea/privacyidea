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
import { Component, computed, DestroyRef, inject, linkedSignal, signal } from "@angular/core";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { DialogAction } from "@models/dialog";

// The browser registration of a WebAuthn or passkey token. A failed attempt can be retried. The final request outlives
// the step, so a step reopened while it runs waits for it.
@Component({
  selector: "app-token-complete-enrollment-fido2",
  templateUrl: "./token-complete-enrollment-fido2.component.html"
})
export class TokenCompleteEnrollmentFido2Component extends EnrollmentStep {
  readonly title = signal($localize`:@@token.takeActionYour:Take Action on Your Authenticator`).asReadonly();
  readonly headerState = "incomplete";

  protected readonly finalizing = computed(() => this.flow.sentInput() !== null);
  protected readonly registrationFailed = linkedSignal(() => this.flow.stepRequestFailed());
  override readonly actions = computed<DialogAction<string>[]>(() =>
    this.registrationFailed()
      ? [{ type: "confirm", label: $localize`:@@token.retry:Retry`, value: "retry", primary: true }]
      : []
  );

  private readonly firstStep = this.flow.firstStep;
  // Leaving the step aborts the browser registration, but not its final request.
  private readonly left = new AbortController();

  constructor() {
    super();
    inject(DestroyRef).onDestroy(() => this.left.abort());
    if (!this.finalizing()) {
      void this.register();
    }
  }

  override onAction(value: string): void {
    if (value === "retry") {
      void this.register();
    }
  }

  private async register(): Promise<void> {
    if (this.firstStep?.kind !== "fido2") {
      return;
    }
    this.registrationFailed.set(false);
    const finalRequest = await this.firstStep.register(this.left.signal).catch(() => null);
    if (this.left.signal.aborted) {
      return;
    }
    if (finalRequest === null) {
      this.registrationFailed.set(true);
      return;
    }
    this.flow.sendStepRequest(finalRequest, (result) => result);
  }
}
