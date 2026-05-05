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
import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl } from "@angular/forms";
import { EnrollApplspecComponent } from "../../token/token-enrollment/enroll-asp/enroll-applspec.component";
import { EnrollCertificateComponent } from "../../token/token-enrollment/enroll-certificate/enroll-certificate.component";
import { EnrollDaypasswordComponent } from "../../token/token-enrollment/enroll-daypassword/enroll-daypassword.component";
import { EnrollEmailComponent } from "../../token/token-enrollment/enroll-email/enroll-email.component";
import { EnrollFoureyesComponent } from "../../token/token-enrollment/enroll-foureyes/enroll-foureyes.component";
import { EnrollHotpComponent } from "../../token/token-enrollment/enroll-hotp/enroll-hotp.component";
import { EnrollIndexedsecretComponent } from "../../token/token-enrollment/enroll-indexsecret/enroll-indexedsecret.component";
import { EnrollMotpComponent } from "../../token/token-enrollment/enroll-motp/enroll-motp.component";
import { EnrollPaperComponent } from "../../token/token-enrollment/enroll-paper/enroll-paper.component";
import { EnrollPasskeyComponent } from "../../token/token-enrollment/enroll-passkey/enroll-passkey.component";
import { EnrollPushComponent } from "../../token/token-enrollment/enroll-push/enroll-push.component";
import { EnrollQuestionComponent } from "../../token/token-enrollment/enroll-questionnaire/enroll-question.component";
import { EnrollRadiusComponent } from "../../token/token-enrollment/enroll-radius/enroll-radius.component";
import { EnrollRegistrationComponent } from "../../token/token-enrollment/enroll-registration/enroll-registration.component";
import { EnrollRemoteComponent } from "../../token/token-enrollment/enroll-remote/enroll-remote.component";
import { EnrollSmsComponent } from "../../token/token-enrollment/enroll-sms/enroll-sms.component";
import { EnrollSpassComponent } from "../../token/token-enrollment/enroll-spass/enroll-spass.component";
import { EnrollSshkeyComponent } from "../../token/token-enrollment/enroll-sshkey/enroll-sshkey.component";
import { EnrollTanComponent } from "../../token/token-enrollment/enroll-tan/enroll-tan.component";
import { EnrollTiqrComponent } from "../../token/token-enrollment/enroll-tiqr/enroll-tiqr.component";
import { EnrollTotpComponent } from "../../token/token-enrollment/enroll-totp/enroll-totp.component";
import { EnrollU2fComponent } from "../../token/token-enrollment/enroll-u2f/enroll-u2f.component";
import { EnrollVascoComponent } from "../../token/token-enrollment/enroll-vasco/enroll-vasco.component";
import { EnrollWebauthnComponent } from "../../token/token-enrollment/enroll-webauthn/enroll-webauthn.component";
import { EnrollYubicoComponent } from "../../token/token-enrollment/enroll-yubico/enroll-yubico.component";
import { EnrollYubikeyComponent } from "../../token/token-enrollment/enroll-yubikey/enroll-yubikey.component";
import type {
  enrollmentArgsGetterFn,
  OnEnrollmentResponseFn,
  ReopenDialogFn
} from "../../token/token-enrollment/token-enrollment.component";

@Component({
  selector: "app-enroll-token-type-switch",
  standalone: true,
  imports: [
    EnrollHotpComponent,
    EnrollTotpComponent,
    EnrollSpassComponent,
    EnrollMotpComponent,
    EnrollSshkeyComponent,
    EnrollYubikeyComponent,
    EnrollRemoteComponent,
    EnrollYubicoComponent,
    EnrollRadiusComponent,
    EnrollSmsComponent,
    EnrollFoureyesComponent,
    EnrollApplspecComponent,
    EnrollDaypasswordComponent,
    EnrollCertificateComponent,
    EnrollEmailComponent,
    EnrollIndexedsecretComponent,
    EnrollPaperComponent,
    EnrollPushComponent,
    EnrollQuestionComponent,
    EnrollRegistrationComponent,
    EnrollTanComponent,
    EnrollTiqrComponent,
    EnrollU2fComponent,
    EnrollVascoComponent,
    EnrollWebauthnComponent,
    EnrollPasskeyComponent
  ],
  templateUrl: "./enroll-token-type-switch.component.html"
})
export class EnrollTokenTypeSwitchComponent {
  @Input({ required: true }) tokenTypeKey!: string;
  @Input() wizard = false;

  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<enrollmentArgsGetterFn>();
  @Output() onEnrollmentResponseChange = new EventEmitter<OnEnrollmentResponseFn>();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();
}

