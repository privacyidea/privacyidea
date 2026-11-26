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
import { computed, inject, signal, Type } from "@angular/core";
import { MatDialogRef } from "@angular/material/dialog";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { TokenCompleteEnrollmentFido2Component } from "@components/token/token-enrollment/token-complete-enrollment-fido2/token-complete-enrollment-fido2.component";
import { TokenCompleteEnrollmentPushComponent } from "@components/token/token-enrollment/token-complete-enrollment-push/token-complete-enrollment-push.component";
import { TokenCompleteEnrollmentTwoStepComponent } from "@components/token/token-enrollment/token-complete-enrollment-two-step/token-complete-enrollment-two-step.component";
import { TokenEnrollmentDialogComponent } from "@components/token/token-enrollment/token-enrollment-dialog/token-enrollment-dialog.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenEnrollmentDialogData } from "@services/token/token.service";
import { defer, finalize, Observable, Subject, tap } from "rxjs";

export type EnrollmentStepKind = "push" | "fido2" | "complete" | "verify" | "success";

/**
 * The step a token type needs right after its first response. Push waits for the app to register and starts again
 * when the dialog is reopened. WebAuthn and passkey run the browser registration, which cannot be reopened: it shows
 * nothing the user keeps, and its challenge expires.
 */
export type EnrollmentFirstStep =
  | { kind: "push" }
  | {
      kind: "fido2";
      // Ends with the response to continue with, ENROLLMENT_CANCELLED once the token was deleted, or null when the
      // registration failed and can be retried. The signal aborts once the step is left.
      register: (signal: AbortSignal) => Promise<EnrollmentStepResult>;
    };

export interface EnrollmentFlowOptions {
  // Read when the success step opens, so a subclass can replace it, see the wizard.
  successStep: () => Type<EnrollmentStep>;
  // A step finished or the dialog closed.
  onStepClosed?: () => void;
  // The incomplete token was deleted.
  onCancelled?: () => void;
  // The dialog was closed before the enrollment finished. The token exists, resume() finishes it if resumable.
  onIncomplete?: () => void;
  onCompleted?: () => void;
}

/**
 * Runs the steps of a token enrollment that follow the first response in one dialog: the first step
 * of the token type (push, WebAuthn, passkey), the two-step completion (rollout state "clientwait"),
 * the verification (a "verify" challenge in the response) and the success step. The server response decides the next step, so the number of steps is not
 * known in advance.
 *
 * Holds the state of the running enrollment, so a closed dialog can be resumed at the same step.
 */
export class EnrollmentFlow {
  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly dialogData = signal<TokenEnrollmentDialogData | null>(null);
  readonly step = signal<EnrollmentStepKind | null>(null);
  readonly stepComponent = computed<Type<EnrollmentStep> | null>(() => {
    switch (this.step()) {
      case "push":
        return TokenCompleteEnrollmentPushComponent;
      case "fido2":
        return TokenCompleteEnrollmentFido2Component;
      case "complete":
        return TokenCompleteEnrollmentTwoStepComponent;
      case "verify":
        return TokenVerifyEnrollmentComponent;
      case "success":
        return this.options.successStep();
      default:
        return null;
    }
  });

  // Set when the dialog opens. A dialog that opens before the success step keeps its size through all steps, one
  // that opens at the success step shows only that and fits its content.
  readonly fixedSize = signal(false);

  // Whether resume() can finish the enrollment once the dialog is closed in the current step.
  readonly resumable = computed(() => this.step() !== "fido2");

  private readonly stepFinishedSubject = new Subject<void>();
  // Emits when the current step is left: for the next step, or because the dialog closed.
  readonly stepFinished: Observable<void> = this.stepFinishedSubject.asObservable();

  // Set until the first step of the token type is done.
  firstStep: EnrollmentFirstStep | null = null;
  // Whether the dialog was opened again with the reopen button, see the push polling.
  reopened = false;
  // The input of the request that finishes the current step, while it runs. It outlives the step, so a reopened
  // step shows what was sent and does not send it again.
  readonly sentInput = signal<string | null>(null);

  private dialogRef: MatDialogRef<unknown> | null = null;
  private cancelled = false;
  // Set from the start of a deletion until the dialog closes, or until the deletion fails.
  private deleting = false;
  // A step result that arrived while the token was being deleted.
  private heldResult: EnrollmentStepResult | undefined = undefined;
  // Counts the enrollments, so a request of an earlier one does not change the current one.
  private run = 0;
  // Set while a step result that arrived after the dialog closed is applied: the next step waits for the reopen.
  private keepClosed = false;

  constructor(private readonly options: EnrollmentFlowOptions) {}

  /**
   * Starts a new enrollment from the response of its first request.
   *
   * @param data The data of the enrolled token for the steps.
   * @param firstStep The step the token type needs first, if any.
   */
  start(
    data: Omit<TokenEnrollmentDialogData, "onEnrollmentResponseChange">,
    firstStep: EnrollmentFirstStep | null = null
  ): void {
    this.newRun();
    this.firstStep = firstStep;
    this.reopened = false;
    this.cancelled = false;
    this.stopHolding();
    this.dialogData.set({
      ...data,
      onEnrollmentResponseChange: (response) => this.setResponse(response)
    });
  }

  reset(): void {
    this.newRun();
    this.firstStep = null;
    this.dialogData.set(null);
  }

  /**
   * Shows the step that the response asks for next.
   *
   * @param response The latest response of the running enrollment.
   */
  continue(response: EnrollmentResponse): void {
    if (!this.dialogData()) {
      return;
    }
    this.setResponse(response);
    if (this.firstStep) {
      this.show(this.firstStep.kind);
      return;
    }
    if (response.detail?.rollout_state !== "clientwait") {
      this.verify(response);
      return;
    }
    this.show("complete");
  }

  // Opens the dialog again at the step it was closed in.
  resume(): void {
    const step = this.step();
    if (step && this.dialogData()) {
      this.reopened = true;
      this.show(step);
      return;
    }
    const response = this.dialogData()?.response;
    if (response) {
      this.continue(response);
    }
  }

  /**
   * Called by a step when it is done.
   *
   * @param result The response to continue with, ENROLLMENT_CANCELLED once the token was deleted, or null to close
   *   the dialog with the enrollment unfinished.
   */
  finishStep(result: EnrollmentStepResult): void {
    if (this.deleting && result !== ENROLLMENT_CANCELLED) {
      this.heldResult = result;
      return;
    }
    if (result === ENROLLMENT_CANCELLED) {
      this.cancelled = true;
      this.close();
      return;
    }
    if (!result) {
      this.close();
      return;
    }
    this.options.onStepClosed?.();
    const step = this.step();
    if (step === "push" || step === "fido2") {
      this.firstStep = null;
      this.continue(result);
      return;
    }
    if (step === "complete") {
      // The data shown for the second step is outdated once the token is complete.
      this.dialogData.update((data) => (data ? { ...data, showEnrollData: false } : data));
      this.verify(result);
      return;
    }
    this.finish(result);
  }

  /**
   * Sends the request that finishes the current step. The request outlives the step: a response that arrives after
   * the dialog closed moves the enrollment on without opening the dialog, and the reopen shows the next step.
   *
   * @param request The request. It has notified about its failure itself.
   * @param toResult The response to continue with, or null if the step is not finished.
   * @param input What the user entered for the request, shown again if the step is reopened while it runs.
   */
  sendStepRequest<T>(request: Observable<T>, toResult: (response: T) => EnrollmentResponse | null, input = ""): void {
    if (this.sentInput() !== null) {
      return;
    }
    const run = this.run;
    this.sentInput.set(input);
    request
      .pipe(
        finalize(() => {
          if (run === this.run) {
            this.sentInput.set(null);
          }
        })
      )
      .subscribe({
        next: (response) => {
          const result = toResult(response);
          if (!result || run !== this.run) {
            return;
          }
          this.keepClosed = !this.dialogRef;
          this.finishStep(result);
          this.keepClosed = false;
        },
        error: () => undefined
      });
  }

  // Closes the dialog without asking. Before the success step, the enrollment stays unfinished.
  close(): void {
    this.dialogRef?.close();
  }

  /**
   * Deletes the token of the running enrollment. A step result that arrives meanwhile, e.g. a push token registered
   * by the app, is held back: dropped once the token is gone, and applied if the deletion fails.
   *
   * @param deletion The request that deletes the token.
   * @returns The deletion, failing as it does.
   */
  deleteToken<T>(deletion: Observable<T>): Observable<T> {
    return defer(() => {
      this.deleting = true;
      return deletion.pipe(tap({ error: () => this.applyHeldResult() }));
    });
  }

  private applyHeldResult(): void {
    const held = this.heldResult;
    this.stopHolding();
    if (held !== undefined) {
      this.finishStep(held);
    }
  }

  private stopHolding(): void {
    this.deleting = false;
    this.heldResult = undefined;
  }

  private verify(response: EnrollmentResponse): void {
    this.setResponse(response);
    if (!response.detail?.verify) {
      this.finish(response);
      return;
    }
    this.show("verify");
  }

  private finish(response: EnrollmentResponse): void {
    this.setResponse(response);
    this.show("success");
    this.options.onCompleted?.();
  }

  private show(step: EnrollmentStepKind): void {
    this.stepFinishedSubject.next();
    this.step.set(step);
    if (!this.dialogRef && !this.keepClosed) {
      this.openDialog();
    }
  }

  private openDialog(): void {
    this.fixedSize.set(this.step() !== "success");
    const dialogRef = this.dialogService.openDialog({
      component: TokenEnrollmentDialogComponent,
      data: { flow: this },
      // The dialog asks before it closes and moves the focus itself on every step.
      configOverride: { disableClose: true, autoFocus: false }
    });
    this.dialogRef = dialogRef;
    dialogRef.afterClosed().subscribe(() => {
      if (this.dialogRef !== dialogRef) {
        return;
      }
      this.dialogRef = null;
      this.stopHolding();
      this.stepFinishedSubject.next();
      this.options.onStepClosed?.();
      if (this.cancelled) {
        this.cancelled = false;
        this.options.onCancelled?.();
        return;
      }
      if (this.step() === "success") {
        return;
      }
      if (!this.resumable()) {
        this.reset();
      }
      this.options.onIncomplete?.();
    });
  }

  private newRun(): void {
    this.run++;
    this.step.set(null);
    this.sentInput.set(null);
  }

  private setResponse(response: EnrollmentResponse): void {
    this.dialogData.update((data) => (data ? { ...data, response } : data));
  }
}
