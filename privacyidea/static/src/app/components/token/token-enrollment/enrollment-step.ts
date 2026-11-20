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
import { Directive, inject, InjectionToken, Signal, signal } from "@angular/core";
import type { EnrollmentFlow } from "@components/token/token-enrollment/enrollment-flow";
import { EnrolledTextState } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { DialogAction } from "@models/dialog";
import { TokenEnrollmentDialogData } from "@services/token/token.service";
import { Observable, of } from "rxjs";

// The enrollment dialog that shows the steps.
export interface EnrollmentStepHost {
  readonly flow: EnrollmentFlow;
  register(step: EnrollmentStep): void;
}

export const ENROLLMENT_STEP_HOST = new InjectionToken<EnrollmentStepHost>("EnrollmentStepHost");

/**
 * The content of one enrollment step. The enrollment dialog around it shows the title, the header,
 * the actions and the way out; the step reports its result to the flow instead of closing a dialog.
 */
@Directive()
export abstract class EnrollmentStep {
  protected readonly flow: EnrollmentFlow = inject(ENROLLMENT_STEP_HOST).flow;
  // The state when the step opened. A regenerated response reaches the step through its enrollment data.
  protected readonly data: TokenEnrollmentDialogData = this.flow.dialogData()!;

  abstract readonly title: Signal<string>;
  abstract readonly headerState: EnrolledTextState;
  readonly actions: Signal<DialogAction<string>[]> = signal([]);
  // False hides Close and ignores Escape and backdrop clicks, see the wizard.
  readonly closable: boolean = true;

  constructor() {
    inject(ENROLLMENT_STEP_HOST).register(this);
  }

  onAction?(value: string): void;

  // Asked before the dialog of a finished enrollment closes. Emits whether it may close.
  confirmClose(): Observable<boolean> {
    return of(true);
  }
}
