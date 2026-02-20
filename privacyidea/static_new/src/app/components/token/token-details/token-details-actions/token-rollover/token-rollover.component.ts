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

import { Component, inject, signal, WritableSignal } from "@angular/core";
import { FormControl, ReactiveFormsModule } from "@angular/forms";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import { MatButton } from "@angular/material/button";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { lastValueFrom } from "rxjs";
import { TokenEnrollmentComponent } from "../../../token-enrollment/token-enrollment.component";
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
import { UserData } from "../../../../../services/user/user.service";
import { TokenEnrollmentLastStepDialogData } from "../../../token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { getTokenApiPayloadMapper } from "../../../../../mappers/token-api-payload/token-api-payload-mapper-registry";

@Component({
  selector: "app-token-rollover",
  imports: [
    ReactiveFormsModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatButton,
    MatDialogClose,
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
    EnrollVascoComponent
  ],
  templateUrl: "./token-rollover.component.html",
  styleUrl: "./token-rollover.component.scss"
})
export class TokenRolloverComponent extends TokenEnrollmentComponent {
  public readonly data = inject(MAT_DIALOG_DATA, { optional: false });
  private dialogRef = inject(MatDialogRef<TokenRolloverComponent>);
  token: WritableSignal<any> = signal(null);
  formControls = signal<{ [key: string]: FormControl<any> }>({});

  constructor() {
    super();
    const mapperObject = getTokenApiPayloadMapper(this.data.token.tokentype);
    if (!mapperObject) {
      return;
    }
    this.token.set(mapperObject.fromTokenDetailsToEnrollmentData(this.data.token));
    this.tokenService.selectedTokenType.set({key: this.token().type, name: "", text: "", info: ""});
  }

  override updateAdditionalFormFields($event: { [key: string]: FormControl<any> }) {
    this.formControls.set($event);
    for (const controlKey of Object.keys($event)) {
      const control = $event[controlKey];
      const patch: { [key: string]: any } = {};
      if (control) {
        patch[controlKey] = control.value;
      }
    }
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
    const onEnrollmentResponseFn = this.onEnrollmentResponse();
    if (onEnrollmentResponseFn && enrollmentResponse) {
      enrollmentResponse = await onEnrollmentResponseFn(enrollmentResponse, enrollmentArgs.data);
    }
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

  protected override openLastStepDialog(args: {
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
      serial: this.serial,
      enrollToken: this.rolloverToken.bind(this),
      user: user,
      userRealm: this.userService.selectedUserRealm(),
      onlyAddToRealm: this.userAssignmentComponent?.onlyAddToRealm() ?? false,
      rollover: rollover ?? true
    };
    this._lastTokenEnrollmentLastStepDialogData.set(dialogData);
    this.dialogService.openTokenEnrollmentLastStepDialog({
      data: dialogData
    });
  }
}
