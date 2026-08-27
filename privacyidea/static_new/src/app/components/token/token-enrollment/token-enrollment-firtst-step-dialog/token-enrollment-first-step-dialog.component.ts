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
import { MatDialogContent, MatDialogState } from "@angular/material/dialog";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { MessageConfirmationDialogComponent } from "@components/shared/dialog/message-confirmation-dialog/message-confirmation-dialog.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { DialogAction } from "@models/dialog";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface TokenEnrollmentFirstStepDialogData {
  enrollmentResponse: EnrollmentResponse;
  showCancelButton?: boolean;
  showCloseButton?: boolean;
  cancelConfirmationMessage?: string;
  registrationFailed?: Signal<boolean>;
  onRetry?: () => void;
}

type FirstStepDialogAction = "retry" | "cancelEnrollment";

@Component({
  selector: "app-token-enrollment-first-step-dialog",
  imports: [MatDialogContent, DialogWrapperComponent],
  templateUrl: "./token-enrollment-first-step-dialog.component.html",
  styleUrl: "./token-enrollment-first-step-dialog.component.scss"
})
export class TokenEnrollmentFirstStepDialogComponent extends AbstractDialogComponent<
  TokenEnrollmentFirstStepDialogData,
  EnrollmentStepResult
> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly Object = Object;

  protected readonly registrationFailed = computed(() => this.data.registrationFailed?.() ?? false);

  protected readonly actions = computed<DialogAction<FirstStepDialogAction>[]>(() => {
    const actions: DialogAction<FirstStepDialogAction>[] = [];
    if (this.data.showCancelButton) {
      actions.push({
        type: "destruct",
        label: $localize`Cancel`,
        value: "cancelEnrollment"
      });
    }
    if (this.data.onRetry && this.registrationFailed()) {
      actions.push({
        type: "confirm",
        label: $localize`Retry`,
        value: "retry",
        primary: true
      });
    }
    return actions;
  });

  protected readonly showCloseButton = this.data.showCloseButton ?? true;

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
    this.dialogService
      .openDialog({
        component: MessageConfirmationDialogComponent,
        data: {
          title: $localize`Cancel Enrollment`,
          message: confirmationMessage,
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (confirmed && this.dialogRef.getState() === MatDialogState.OPEN) {
          this.deleteIncompleteToken(tokenSerial);
        }
      });
  }

  private deleteIncompleteToken(tokenSerial: string): void {
    this.tokenService.cancelEnrollment(tokenSerial).subscribe({
      next: () => this.close(ENROLLMENT_CANCELLED)
    });
  }

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.contentService.tokenSelected(tokenSerial);
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.navigateContainerDetails(containerSerial);
  }
}
