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

import { Component, forwardRef, inject, signal } from "@angular/core";
import { MatDialogRef } from "@angular/material/dialog";
import { PiResponse } from "@app/app.component";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { PushApiPayloadMapper, PushEnrollmentData } from "@app/mappers/token-api-payload/push-token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import {
  TokenEnrollmentFirstStepDialogComponent,
  TokenEnrollmentFirstStepDialogData
} from "@components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenService, TokenServiceInterface, Tokens } from "@services/token/token.service";
import { lastValueFrom } from "rxjs";

@Component({
  selector: "app-enroll-push",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-push.component.html",
  styleUrl: "./enroll-push.component.scss",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollPushComponent) }]
})
export class EnrollPushComponent extends EnrollTokenBase<PushEnrollmentData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly enrollmentMapper: PushApiPayloadMapper = inject(PushApiPayloadMapper);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  pollResponse = signal<PiResponse<Tokens> | undefined>(undefined);

  text = this.tokenService.tokenTypeOptions().find((type) => type.key === "push")?.text;

  firstStepDialogRef: MatDialogRef<
    AbstractDialogComponent<TokenEnrollmentFirstStepDialogData, EnrollmentStepResult>,
    EnrollmentStepResult
  > | null = null;

  override readonly showEnrollDataInLastStep: boolean = false;

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<PushEnrollmentData> | null {
    const enrollmentData: PushEnrollmentData = {
      ...basicOptions,
      type: "push"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  override async onEnrollmentResponse(
    initResponse: EnrollmentResponse,
    enrollmentData?: TokenEnrollmentData
  ): Promise<EnrollmentStepResult> {
    if (!initResponse) {
      return null;
    }
    return this.awaitRolloutState(initResponse, 5000, enrollmentData?.rollover ?? false);
  }

  private async awaitRolloutState(
    initResponse: EnrollmentResponse,
    initDelay: number,
    rollover: boolean
  ): Promise<EnrollmentStepResult> {
    const dialogRef = this._openStepOneDialog(initResponse, rollover);
    this.firstStepDialogRef = dialogRef;

    let lastPollResponse: PiResponse<Tokens> | undefined;
    this.tokenService.pollTokenRolloutState({ tokenSerial: initResponse.detail.serial, initDelay }).subscribe({
      next: (pollResponse) => {
        lastPollResponse = pollResponse;
        this.pollResponse.set(pollResponse);
        if (pollResponse.result?.value?.tokens[0].rollout_state !== "clientwait") {
          dialogRef.close();
        }
      },
      error: () => dialogRef.close()
    });

    const dialogResult = await lastValueFrom(dialogRef.afterClosed());
    this.tokenService.stopPolling();
    this.pollResponse.set(undefined);

    if (dialogResult === ENROLLMENT_CANCELLED) {
      this.reopenDialog.set(undefined);
      return ENROLLMENT_CANCELLED;
    }

    const rolloutState = lastPollResponse?.result?.value?.tokens[0].rollout_state ?? initResponse.detail.rollout_state;
    if (rolloutState === "clientwait") {
      return null;
    }
    return {
      ...initResponse,
      detail: {
        ...initResponse.detail,
        rollout_state: rolloutState
      }
    };
  }

  private _openStepOneDialog(
    enrollmentResponse: EnrollmentResponse,
    rollover: boolean
  ): MatDialogRef<
    AbstractDialogComponent<TokenEnrollmentFirstStepDialogData, EnrollmentStepResult>,
    EnrollmentStepResult
  > {
    this.reopenDialog.set(async () => {
      if (this.firstStepDialogRef && this.dialogService.isDialogOpen(this.firstStepDialogRef)) {
        return null;
      }
      return this.awaitRolloutState(enrollmentResponse, 0, rollover);
    });

    return this.dialogService.openDialog({
      component: TokenEnrollmentFirstStepDialogComponent,
      data: {
        enrollmentResponse,
        showCancelButton: !rollover && this.authService.actionAllowed("delete"),
        showCloseButton: true
      }
    });
  }
}
