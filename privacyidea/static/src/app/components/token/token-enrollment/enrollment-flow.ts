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
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentDialogComponent } from "@components/token/token-enrollment/token-enrollment-dialog/token-enrollment-dialog.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenEnrollmentDialogData } from "@services/token/token.service";
import { Observable, Subject } from "rxjs";

export type EnrollmentStepKind = "complete" | "verify" | "success";

export interface EnrollmentFlowOptions {
  // Read when the success step opens, so a subclass can replace it, see the wizard.
  successStep: () => Type<EnrollmentStep>;
  // A reason given here keeps the success step closed and is shown as a warning.
  successBlockedReason?: () => string | null;
  // A step finished or the dialog closed.
  onStepClosed?: () => void;
  // The incomplete token was deleted.
  onCancelled?: () => void;
  // The dialog was closed before the enrollment finished. The token exists, resume() finishes it.
  onIncomplete?: () => void;
  onCompleted?: () => void;
}

/**
 * Runs the steps of a token enrollment that follow the first response in one dialog: the two-step
 * completion (rollout state "clientwait"), the verification (a "verify" challenge in the response)
 * and the success step. The server response decides the next step, so the number of steps is not
 * known in advance.
 *
 * Holds the state of the running enrollment, so a closed dialog can be resumed at the same step.
 */
export class EnrollmentFlow {
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly dialogData = signal<TokenEnrollmentDialogData | null>(null);
  readonly step = signal<EnrollmentStepKind | null>(null);
  readonly stepComponent = computed<Type<EnrollmentStep> | null>(() => {
    switch (this.step()) {
      case "complete":
        return TokenCompleteEnrollmentComponent;
      case "verify":
        return TokenVerifyEnrollmentComponent;
      case "success":
        return this.options.successStep();
      default:
        return null;
    }
  });

  private readonly stepFinishedSubject = new Subject<void>();
  // Emits when the current step is left: for the next step, or because the dialog closed.
  readonly stepFinished: Observable<void> = this.stepFinishedSubject.asObservable();

  private dialogRef: MatDialogRef<unknown> | null = null;
  private cancelled = false;

  constructor(private readonly options: EnrollmentFlowOptions) {}

  /**
   * Starts a new enrollment from the response of its first request.
   *
   * @param data The data of the enrolled token for the steps.
   */
  start(data: Omit<TokenEnrollmentDialogData, "onEnrollmentResponseChange">): void {
    this.step.set(null);
    this.dialogData.set({
      ...data,
      onEnrollmentResponseChange: (response) => this.setResponse(response)
    });
  }

  reset(): void {
    this.step.set(null);
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
    if (this.step() === "complete") {
      // The data shown for the second step is outdated once the token is complete.
      this.dialogData.update((data) => (data ? { ...data, showEnrollData: false } : data));
      this.verify(result);
      return;
    }
    this.finish(result);
  }

  // Closes the dialog without asking. Before the success step, the enrollment stays unfinished.
  close(): void {
    this.dialogRef?.close();
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
    const blockedReason = this.options.successBlockedReason?.();
    if (blockedReason) {
      this.notificationService.warning(blockedReason);
      this.close();
      return;
    }
    this.setResponse(response);
    this.show("success");
    this.options.onCompleted?.();
  }

  private show(step: EnrollmentStepKind): void {
    this.stepFinishedSubject.next();
    this.step.set(step);
    if (!this.dialogRef) {
      this.openDialog();
    }
  }

  private openDialog(): void {
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
      this.stepFinishedSubject.next();
      this.options.onStepClosed?.();
      if (this.cancelled) {
        this.cancelled = false;
        this.options.onCancelled?.();
        return;
      }
      if (this.step() !== "success") {
        this.options.onIncomplete?.();
      }
    });
  }

  private setResponse(response: EnrollmentResponse): void {
    this.dialogData.update((data) => (data ? { ...data, response } : data));
  }
}
