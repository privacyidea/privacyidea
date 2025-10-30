/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, WritableSignal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogTitle } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { EnrollmentResponse } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { TokenType } from "../../../../services/token/token.service";
import { UserData } from "../../../../services/user/user.service";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";
import { QrCodeTextComponent } from "./qr-code-text/qr-code-text.component";
import { OtpKeyComponent } from "./otp-key/otp-key.component";
import { TiqrEnrollUrlComponent } from "./tiqr-enroll-url/tiqr-enroll-url.component";
import { RegistrationCodeComponent } from "./registration-code/registration-code.component";
import { OtpValuesComponent } from "./otp-values/otp-values.component";

export type TokenEnrollmentLastStepDialogData = {
  tokentype: TokenType;
  response: EnrollmentResponse;
  serial: WritableSignal<string | null>;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: "app-token-enrollment-last-step-dialog-self-service",
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatIcon,
    QrCodeTextComponent,
    OtpKeyComponent,
    TiqrEnrollUrlComponent,
    RegistrationCodeComponent,
    OtpValuesComponent
  ],
  templateUrl: "./token-enrollment-last-step-dialog.self-service.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss"
})
export class TokenEnrollmentLastStepDialogSelfServiceComponent extends TokenEnrollmentLastStepDialogComponent {
}