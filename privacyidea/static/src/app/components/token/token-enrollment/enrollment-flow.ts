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
import { ComponentType } from "@angular/cdk/overlay";
import { inject, signal } from "@angular/core";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenEnrollmentDialogData } from "@services/token/token.service";

export interface EnrollmentFlowOptions {
  // Read when the success dialog opens, so a subclass can replace it, see the wizard.
  successDialog: () => ComponentType<AbstractDialogComponent<TokenEnrollmentDialogData>>;
  // A reason given here keeps the success dialog closed and is shown as a warning.
  successBlockedReason?: () => string | null;
  onStepClosed?: () => void;
  // The incomplete token was deleted.
  onCancelled?: () => void;
  // A step was closed before the enrollment finished. The token exists, resume() finishes it.
  onIncomplete?: () => void;
  onCompleted?: () => void;
}

/**
 * Runs the steps of a token enrollment that follow the first response: the two-step completion
 * (rollout state "clientwait"), the verification (a "verify" challenge in the response) and the
 * success dialog. The server response decides the next step, so the number of steps is not known in
 * advance.
 *
 * Holds the state of the running enrollment, so a closed step can be resumed later.
 */
export class EnrollmentFlow {
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly dialogData = signal<TokenEnrollmentDialogData | null>(null);

  constructor(private readonly options: EnrollmentFlowOptions) {}

  /**
   * Starts a new enrollment from the response of its first request.
   *
   * @param data The data of the enrolled token for the step dialogs.
   */
  start(data: Omit<TokenEnrollmentDialogData, "onEnrollmentResponseChange">): void {
    this.dialogData.set({
      ...data,
      onEnrollmentResponseChange: (response) => this.setResponse(response)
    });
  }

  reset(): void {
    this.dialogData.set(null);
  }

  /**
   * Opens the step that the response asks for next.
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
    this.openStep(TokenCompleteEnrollmentComponent, (result) => {
      // The data shown for the second step is outdated once the token is complete.
      this.dialogData.update((data) => (data ? { ...data, showEnrollData: false } : data));
      this.verify(result);
    });
  }

  // Opens the step again that was closed before the enrollment finished.
  resume(): void {
    const response = this.dialogData()?.response;
    if (response) {
      this.continue(response);
    }
  }

  private verify(response: EnrollmentResponse): void {
    this.setResponse(response);
    if (!response.detail?.verify) {
      this.finish(response);
      return;
    }
    this.openStep(TokenVerifyEnrollmentComponent, (result) => this.finish(result));
  }

  private finish(response: EnrollmentResponse): void {
    const blockedReason = this.options.successBlockedReason?.();
    if (blockedReason) {
      this.notificationService.warning(blockedReason);
      return;
    }
    this.setResponse(response);
    this.dialogService
      .openDialog({ component: this.options.successDialog(), data: this.dialogData()! })
      .afterClosed()
      .subscribe(() => this.options.onStepClosed?.());
    this.options.onCompleted?.();
  }

  private openStep(
    component: ComponentType<AbstractDialogComponent<TokenEnrollmentDialogData, EnrollmentStepResult>>,
    next: (response: EnrollmentResponse) => void
  ): void {
    const dialogRef = this.dialogService.openDialog({
      component,
      data: this.dialogData()!,
      configOverride: { autoFocus: "input", disableClose: true }
    });
    dialogRef.afterClosed().subscribe((result) => {
      this.options.onStepClosed?.();
      if (result === ENROLLMENT_CANCELLED) {
        this.options.onCancelled?.();
        return;
      }
      if (!result) {
        this.options.onIncomplete?.();
        return;
      }
      next(result);
    });
  }

  private setResponse(response: EnrollmentResponse): void {
    this.dialogData.update((data) => (data ? { ...data, response } : data));
  }
}
