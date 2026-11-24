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
import { Component, computed, inject, Signal } from "@angular/core";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { MessageConfirmationDialogComponent } from "@components/shared/dialog/message-confirmation-dialog/message-confirmation-dialog.component";
import {
  closeWithStep,
  confirmLeaveIncompleteStep
} from "@components/token/token-enrollment/leave-incomplete-enrollment";
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { EnrollmentCustomizationFrameComponent } from "@components/token/token-enrollment/enrollment-customization-frame/enrollment-customization-frame.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { DialogAction } from "@models/dialog";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface TokenEnrollmentFirstStepDialogData {
  enrollmentResponse: EnrollmentResponse;
  // The enrollment request, for the user and realm in the header.
  enrollmentData?: TokenEnrollmentData;
  showCancelButton?: boolean;
  wizard?: boolean;
  cancelConfirmationMessage?: string;
  registrationFailed?: Signal<boolean>;
  onRetry?: () => void;
}

type FirstStepDialogAction = "retry" | "cancelEnrollment";

@Component({
  selector: "app-token-enrollment-first-step-dialog",
  imports: [DialogWrapperComponent, EnrollmentCustomizationFrameComponent, TokenEnrolledTextComponent],
  templateUrl: "./token-enrollment-first-step-dialog.component.html"
})
export class TokenEnrollmentFirstStepDialogComponent extends AbstractDialogComponent<
  TokenEnrollmentFirstStepDialogData,
  EnrollmentStepResult
> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly wizard = this.data.wizard ?? false;
  // A link leaves like Close; where Cancel replaces Close, it asks what happens to the token.
  protected readonly confirmLeave = confirmLeaveIncompleteStep({
    dialogService: this.dialogService,
    tokenService: this.tokenService,
    serial: () => this.data.enrollmentResponse.detail?.serial,
    canCancel: () => !!this.data.showCancelButton,
    close: (result) => this.dialogRef.close(result),
    stepClosed: () => this.dialogRef.afterClosed()
  });

  protected readonly registrationFailed = computed(() => this.data.registrationFailed?.() ?? false);

  protected readonly actions = computed<DialogAction<FirstStepDialogAction>[]>(() => {
    const actions: DialogAction<FirstStepDialogAction>[] = [];
    if (this.data.showCancelButton) {
      actions.push({
        type: "destruct",
        label: $localize`:@@common.cancel:Cancel`,
        value: "cancelEnrollment"
      });
    }
    if (this.data.onRetry && this.registrationFailed()) {
      actions.push({
        type: "confirm",
        label: $localize`:@@token.retry:Retry`,
        value: "retry",
        primary: true
      });
    }
    return actions;
  });

  onAction(action: FirstStepDialogAction): void {
    if (action === "retry") {
      this.data.onRetry?.();
      return;
    }
    this.cancelEnrollment();
  }

  cancelEnrollment(): void {
    const tokenSerial = this.data.enrollmentResponse.detail?.serial;
    if (!tokenSerial) {
      return;
    }
    const confirmationMessage = this.data.cancelConfirmationMessage;
    if (!confirmationMessage) {
      this.deleteIncompleteToken(tokenSerial);
      return;
    }
    const questionRef = this.dialogService.openDialog({
      component: MessageConfirmationDialogComponent,
      data: {
        title: $localize`:@@token.cancelEnrollment:Cancel Enrollment`,
        message: confirmationMessage,
        confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
      }
    });
    closeWithStep(questionRef, this.dialogRef.afterClosed());
    questionRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) {
        this.deleteIncompleteToken(tokenSerial);
      }
    });
  }

  private deleteIncompleteToken(tokenSerial: string): void {
    this.tokenService.cancelEnrollment(tokenSerial).subscribe({
      next: () => this.close(ENROLLMENT_CANCELLED),
      error: () => undefined
    });
  }
}
