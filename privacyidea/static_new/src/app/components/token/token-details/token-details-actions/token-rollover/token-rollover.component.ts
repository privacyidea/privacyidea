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

import { Component, WritableSignal, computed, inject, signal, viewChild } from "@angular/core";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { getTokenApiPayloadMapper } from "@app/mappers/token-api-payload/token-api-payload-mapper-registry";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { DialogAction } from "@models/dialog";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import {
  TokenDetails,
  TokenEnrollmentDialogData,
  TokenService,
  TokenServiceInterface
} from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { Observable, lastValueFrom } from "rxjs";

@Component({
  selector: "app-token-rollover",
  imports: [DialogWrapperComponent, EnrollTokenTypeSwitchComponent],
  standalone: true,
  templateUrl: "./token-rollover.component.html",
  styleUrl: "./token-rollover.component.scss"
})
export class TokenRolloverComponent extends AbstractDialogComponent<
  {
    token: TokenDetails;
  },
  boolean
> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  token: WritableSignal<TokenEnrollmentData | null> = signal(null);
  title = computed(() => $localize`Rollover Token` + " " + (this.token()?.serial || ""));
  serial = signal<string | null | undefined>(null);
  enrolledDialogData: WritableSignal<TokenEnrollmentDialogData | null> = signal(null);

  dialogActions = signal<DialogAction<boolean>[]>([
    {
      type: "confirm",
      label: $localize`Rollover`,
      value: true,
      disabled: false
    }
  ]);

  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);

  // Only required if we later add the reopen rollover dialog function
  enrollResponse: WritableSignal<EnrollmentResponse | null> = signal(null);

  constructor() {
    super();
    const mapperObject = getTokenApiPayloadMapper(this.data.token.tokentype);
    if (!mapperObject) {
      return;
    }
    this.token.set(mapperObject.fromTokenDetailsToEnrollmentData(this.data.token));
    this.tokenService.selectedTokenType.set({ key: this.token()!.type, name: "", text: "", info: "" });
    this.serial.set(this.token()!.serial);
  }

  private _toPromise<T>(observable: Observable<T> | Promise<T>): Promise<T> {
    if (observable instanceof Promise) {
      return observable;
    } else {
      return lastValueFrom(observable);
    }
  }

  async rolloverToken() {
    if (!this.token()) {
      this.notificationService.warning("No token selected for rollover.");
      return;
    }

    const strategy = this.enrollSwitch()?.currentStrategy();
    if (!strategy) {
      this.notificationService.warning("Rollover action is not available for the selected token type.");
      return;
    }

    const basicOptions: TokenEnrollmentData = {
      type: this.token()!.type,
      serial: this.token()!.serial,
      description: this.token()!.description,
      rollover: true
    };

    const enrollmentArgs = strategy.buildEnrollmentArgs(basicOptions);
    if (!enrollmentArgs) return;
    const enrollResponse = this.tokenService.enrollToken(enrollmentArgs);

    const enrollPromise = this._toPromise(enrollResponse);

    enrollPromise.catch((error) => {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.error(`Failed to enroll token: ${message || error.message || error}`);
    });
    let enrollmentResponse: EnrollmentResponse | null = await enrollPromise;

    this.enrolledDialogData.set({
      response: enrollmentResponse,
      enrollParameters: enrollmentArgs,
      tokenType: this.tokenService.selectedTokenType().key,
      rollover: true
    });

    // Complete rollover
    // Push, passkey, webauthn (TODO: maybe we can integrate this into the complete enrollment dialog component)
    if (strategy.onEnrollmentResponse && enrollmentResponse) {
      enrollmentResponse = await strategy.onEnrollmentResponse(enrollmentResponse, enrollmentArgs.data);
    }

    // two step enrollment + handles further enrollment steps (verify + success dialog)
    this.dialogRef.close();
    this.handleCompleteEnrollment(enrollmentResponse);
  }

  handleCompleteEnrollment(enrollmentResponse: EnrollmentResponse | null): void {
    if (!this.enrolledDialogData() || !enrollmentResponse) return;

    this.enrollResponse.set(enrollmentResponse);
    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: enrollmentResponse
    });

    if (enrollmentResponse?.detail.rollout_state !== "clientwait") {
      return this.handleVerifyEnrollment(enrollmentResponse);
    }

    const dialogRef = this.dialogService.openDialog({
      component: TokenCompleteEnrollmentComponent,
      data: this.enrolledDialogData()
    });
    dialogRef.afterClosed().subscribe((result) => {
      this.tokenService.tokenDetailResource.reload();
      if (result) {
        this.enrollResponse.set(result);
        this.enrolledDialogData.set({
          ...this.enrolledDialogData()!,
          showEnrollData: false
        });
        this.handleVerifyEnrollment(result);
      }
    });
  }

  handleVerifyEnrollment(enrollmentResponse: EnrollmentResponse | null): void {
    if (!this.enrolledDialogData() || !enrollmentResponse) return;

    this.enrollResponse.set(enrollmentResponse);
    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: enrollmentResponse
    });

    if (!enrollmentResponse?.detail?.verify) {
      // No verify required, directly open last step dialog
      return this._handleEnrollmentResponse(enrollmentResponse);
    }

    // Open verify dialog
    const dialogRef = this.dialogService.openDialog({
      component: TokenVerifyEnrollmentComponent,
      data: this.enrolledDialogData()
    });
    dialogRef.afterClosed().subscribe((result) => {
      this.tokenService.tokenDetailResource.reload();
      if (result) {
        this.enrollResponse.set(result);
        this._handleEnrollmentResponse(result);
      }
    });
  }

  protected openLastStepDialog(response: EnrollmentResponse | null): void {
    if (!response) {
      this.notificationService.warning("No rollover response available.");
      return;
    }

    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: response
    });

    const dialogRef = this.dialogService.openDialog({
      component: TokenEnrollmentLastStepDialogComponent,
      data: this.enrolledDialogData()
    });

    dialogRef.afterClosed().subscribe(() => {
      this.tokenService.tokenDetailResource.reload();
    });
  }

  protected _handleEnrollmentResponse(response: EnrollmentResponse): void {
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === "clientwait") {
      return;
    }

    this.openLastStepDialog(response);
  }

}
