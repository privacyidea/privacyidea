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

import { Component, computed, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { FormGroup, ReactiveFormsModule } from "@angular/forms";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { lastValueFrom } from "rxjs";
import { enrollmentArgsGetterFn } from "../../../token-enrollment/token-enrollment.component";
import { EnrollApplspecComponent } from "../../../token-enrollment/enroll-asp/enroll-applspec.component";
import { EnrollDaypasswordComponent } from "../../../token-enrollment/enroll-daypassword/enroll-daypassword.component";
import { EnrollEmailComponent } from "../../../token-enrollment/enroll-email/enroll-email.component";
import { EnrollHotpComponent } from "../../../token-enrollment/enroll-hotp/enroll-hotp.component";
import { EnrollIndexedsecretComponent } from "../../../token-enrollment/enroll-indexsecret/enroll-indexedsecret.component";
import { EnrollMotpComponent } from "../../../token-enrollment/enroll-motp/enroll-motp.component";
import { EnrollPaperComponent } from "../../../token-enrollment/enroll-paper/enroll-paper.component";
import { EnrollQuestionComponent } from "../../../token-enrollment/enroll-questionnaire/enroll-question.component";
import { EnrollRegistrationComponent } from "../../../token-enrollment/enroll-registration/enroll-registration.component";
import { EnrollSmsComponent } from "../../../token-enrollment/enroll-sms/enroll-sms.component";
import { EnrollSpassComponent } from "../../../token-enrollment/enroll-spass/enroll-spass.component";
import { EnrollSshkeyComponent } from "../../../token-enrollment/enroll-sshkey/enroll-sshkey.component";
import { EnrollTanComponent } from "../../../token-enrollment/enroll-tan/enroll-tan.component";
import { EnrollTiqrComponent } from "../../../token-enrollment/enroll-tiqr/enroll-tiqr.component";
import { EnrollTotpComponent } from "../../../token-enrollment/enroll-totp/enroll-totp.component";
import { EnrollU2fComponent } from "../../../token-enrollment/enroll-u2f/enroll-u2f.component";
import { EnrollVascoComponent } from "../../../token-enrollment/enroll-vasco/enroll-vasco.component";
import { UserData, UserService, UserServiceInterface } from "../../../../../services/user/user.service";
import { getTokenApiPayloadMapper } from "../../../../../mappers/token-api-payload/token-api-payload-mapper-registry";
import { TokenEnrollmentLastStepDialogData } from "../../../token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component";
import { TokenEnrollmentLastStepDialogComponent } from "../../../token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { DialogWrapperComponent } from "../../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "../../../../../models/dialog";
import { AbstractDialogComponent } from "../../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../../services/notification/notification.service";
import { DialogService, DialogServiceInterface } from "../../../../../services/dialog/dialog.service";
import { $localize } from "@angular/localize/init";

@Component({
  selector: "app-token-rollover",
  imports: [
    ReactiveFormsModule,
    EnrollApplspecComponent,
    EnrollDaypasswordComponent,
    EnrollEmailComponent,
    EnrollHotpComponent,
    EnrollIndexedsecretComponent,
    EnrollMotpComponent,
    EnrollPaperComponent,
    EnrollQuestionComponent,
    EnrollRegistrationComponent,
    EnrollSmsComponent,
    EnrollSpassComponent,
    EnrollSshkeyComponent,
    EnrollTanComponent,
    EnrollTiqrComponent,
    EnrollTotpComponent,
    EnrollU2fComponent,
    EnrollVascoComponent,
    DialogWrapperComponent
  ],
  standalone: true,
  templateUrl: "./token-rollover.component.html",
  styleUrl: "./token-rollover.component.scss"
})
export class TokenRolloverComponent extends AbstractDialogComponent<{
  token: TokenDetails
}, boolean> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  token: WritableSignal<any> = signal(null);
  title = computed(() => $localize`Rollover Token` + " " + (this.token()?.serial || ""));

  formGroup = new FormGroup({});

  formGroupInvalid = signal(true);

  dialogActions = linkedSignal({
    source: this.formGroupInvalid,
    computation: (invalid) => {
      return [{
        type: "confirm",
        label: $localize`Rollover`,
        value: true,
        disabled: invalid
      }] as DialogAction<boolean>[];
    }
  });

  // Only required if we later add the reopen rollover dialog function
  enrollResponse: WritableSignal<EnrollmentResponse | null> = signal(null);
  _lastTokenEnrollmentLastStepDialogData: WritableSignal<TokenEnrollmentLastStepDialogData | null> = linkedSignal({
    source: this.tokenService.selectedTokenType,
    computation: () => null
  });

  constructor() {
    super();
    const mapperObject = getTokenApiPayloadMapper(this.data.token.tokentype);
    if (!mapperObject) {
      return;
    }
    this.token.set(mapperObject.fromTokenDetailsToEnrollmentData(this.data.token));
    this.tokenService.selectedTokenType.set({ key: this.token().type, name: "", text: "", info: "" });
    this.formGroupInvalid.set(this.formGroup.invalid);
    this.formGroup.statusChanges.subscribe(() => {
      this.formGroupInvalid.set(this.formGroup.invalid);
    });
  }

  enrollmentArgsGetter?: enrollmentArgsGetterFn;

  updateEnrollmentArgsGetter(event: enrollmentArgsGetterFn): void {
    this.enrollmentArgsGetter = event;
  }

  async rolloverToken() {
    if (!this.token()) {
      this.notificationService.openSnackBar("No token selected for rollover.");
      return;
    }

    if (!this.enrollmentArgsGetter) {
      this.notificationService.openSnackBar("Rollover action is not available for the selected token type.");
      return;
    }

    const basicOptions: TokenEnrollmentData = {
      type: this.token()!.type,
      serial: this.token()!.serial,
      rollover: true
    };

    const enrollmentArgs = this.enrollmentArgsGetter(basicOptions);
    if (!enrollmentArgs) return;
    const enrollResponse = this.tokenService.enrollToken(enrollmentArgs);

    let enrollPromise: Promise<EnrollmentResponse | null>;
    if (enrollResponse instanceof Promise) {
      enrollPromise = enrollResponse;
    } else {
      enrollPromise = lastValueFrom(enrollResponse);
    }

    enrollPromise.catch((error) => {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.openSnackBar(`Failed to rollover token: ${message || error.message || error}`);
    });
    let enrollmentResponse = await enrollPromise;

    this.enrollResponse.set(enrollmentResponse);
    if (enrollmentResponse) {
      this._handleEnrollmentResponse({
        response: enrollmentResponse,
        user: null,
        rollover: true
      });
      this.tokenService.tokenDetailResource.reload();
      this.dialogRef.close();
    }
  }

  protected openLastStepDialog(args: {
    response: EnrollmentResponse | null;
    user: UserData | null;
    rollover?: boolean | null
  }): void {
    const { response, user, rollover } = args;
    if (!response) {
      this.notificationService.openSnackBar("No rollover response available.");
      return;
    }

    const dialogData: TokenEnrollmentLastStepDialogData = {
      tokentype: { key: this.token().type, name: "", info: "", text: "" },
      response: response,
      serial: this.token().serial,
      enrollToken: this.rolloverToken.bind(this),
      user: user,
      userRealm: this.userService.selectedUserRealm(),
      onlyAddToRealm: false,
      rollover: rollover ?? true
    };
    this._lastTokenEnrollmentLastStepDialogData.set(dialogData);

    this.dialogService.openDialog({
      component: TokenEnrollmentLastStepDialogComponent,
      data: dialogData
    });
  }

  protected _handleEnrollmentResponse(args: {
    response: EnrollmentResponse;
    user: UserData | null;
    rollover?: boolean
  }): void {
    const { response, user, rollover } = args;
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === "clientwait") {
      return;
    }

    this.openLastStepDialog({ response, user, rollover });
  }

  updateAdditionalFormFields(event: { [key: string]: any }): void {
    // Remove all existing controls from the formGroup
    Object.keys(this.formGroup.controls).forEach(key => {
      this.formGroup.removeControl(key);
    });
    // Add new controls from the event
    for (const key in event) {
      if (event.hasOwnProperty(key) && event[key] && typeof event[key].setValue === "function") {
        this.formGroup.addControl(key, event[key]);
      } else {
        console.warn(`Ignoring invalid form control for key "${key}" emitted by child component.`);
      }
    }
    this.formGroupInvalid.set(this.formGroup.invalid);
  }

}

