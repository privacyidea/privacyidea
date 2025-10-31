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
import { AsyncPipe, NgClass } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, computed, inject } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatNativeDateModule } from "@angular/material/core";
import { MatDatepickerModule } from "@angular/material/datepicker";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { DomSanitizer } from "@angular/platform-browser";
import { catchError, map, of } from "rxjs";
import { EnrollmentResponse } from "../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface, TokenType } from "../../../services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { EnrollApplspecComponent } from "./enroll-asp/enroll-applspec.component";
import { EnrollCertificateComponent } from "./enroll-certificate/enroll-certificate.component";
import { EnrollDaypasswordComponent } from "./enroll-daypassword/enroll-daypassword.component";
import { EnrollEmailComponent } from "./enroll-email/enroll-email.component";
import { EnrollFoureyesComponent } from "./enroll-foureyes/enroll-foureyes.component";
import { EnrollHotpComponent } from "./enroll-hotp/enroll-hotp.component";
import { EnrollIndexedsecretComponent } from "./enroll-indexsecret/enroll-indexedsecret.component";
import { EnrollMotpComponent } from "./enroll-motp/enroll-motp.component";
import { EnrollPaperComponent } from "./enroll-paper/enroll-paper.component";
import { EnrollPasskeyComponent } from "./enroll-passkey/enroll-passkey.component";
import { EnrollPushComponent } from "./enroll-push/enroll-push.component";
import { EnrollQuestionComponent } from "./enroll-questionnaire/enroll-question.component";
import { EnrollRadiusComponent } from "./enroll-radius/enroll-radius.component";
import { EnrollRegistrationComponent } from "./enroll-registration/enroll-registration.component";
import { EnrollRemoteComponent } from "./enroll-remote/enroll-remote.component";
import { EnrollSmsComponent } from "./enroll-sms/enroll-sms.component";
import { EnrollSpassComponent } from "./enroll-spass/enroll-spass.component";
import { EnrollSshkeyComponent } from "./enroll-sshkey/enroll-sshkey.component";
import { EnrollTanComponent } from "./enroll-tan/enroll-tan.component";
import { EnrollTiqrComponent } from "./enroll-tiqr/enroll-tiqr.component";
import { EnrollTotpComponent } from "./enroll-totp/enroll-totp.component";
import { EnrollU2fComponent } from "./enroll-u2f/enroll-u2f.component";
import { EnrollVascoComponent } from "./enroll-vasco/enroll-vasco.component";
import { EnrollWebauthnComponent } from "./enroll-webauthn/enroll-webauthn.component";
import { EnrollYubicoComponent } from "./enroll-yubico/enroll-yubico.component";
import { EnrollYubikeyComponent } from "./enroll-yubikey/enroll-yubikey.component";
import { TokenEnrollmentComponent } from "./token-enrollment.component";
import { AuthService } from "../../../services/auth/auth.service";
import { TokenEnrollmentLastStepDialogData } from "./token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { tokenTypes } from "../../../utils/token.utils";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { environment } from "../../../../environments/environment";

@Component({
  selector: "app-token-enrollment-wizard",
  imports: [
    ReactiveFormsModule,
    FormsModule,
    EnrollHotpComponent,
    MatNativeDateModule,
    MatDatepickerModule,
    MatButton,
    MatIcon,
    EnrollTotpComponent,
    MatIconButton,
    EnrollSpassComponent,
    EnrollMotpComponent,
    NgClass,
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
    EnrollPasskeyComponent,
    AsyncPipe,
    MatTooltip,
    ScrollToTopDirective,
    MatFormField,
    MatInput,
    MatLabel
  ],
  templateUrl: "./token-enrollment.wizard.component.html",
  styleUrl: "./token-enrollment.component.scss"
})
export class TokenEnrollmentWizardComponent extends TokenEnrollmentComponent {
  protected readonly http: HttpClient = inject(HttpClient);
  protected readonly sanitizer: DomSanitizer = inject(DomSanitizer);
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected override readonly realmService: RealmServiceInterface = inject(RealmService);
  protected override readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected override readonly userService: UserServiceInterface = inject(UserService);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected override readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);
  protected override readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected override readonly authService: AuthService = inject(AuthService);
  protected override wizard = true;
  protected readonly tokenType = computed(() => {
    const defaultType = this.authService.defaultTokentype() || "hotp";
    return tokenTypes.find((type) => type.key === defaultType) ||
      { key: defaultType, name: defaultType, info: "", text: "" } as TokenType;
  });


  protected override openLastStepDialog(args: { response: EnrollmentResponse | null; user: UserData | null }): void {
    const { response, user } = args;
    if (!response) {
      this.notificationService.openSnackBar("No enrollment response available.");
      return;
    }

    const dialogData: TokenEnrollmentLastStepDialogData = {
      tokentype: this.tokenType(),
      response: response,
      serial: this.serial,
      enrollToken: this.enrollToken.bind(this),
      user: user,
      userRealm: this.userService.selectedUserRealm(),
      onlyAddToRealm: this.onlyAddToRealmControl.value
    };
    this._lastTokenEnrollmentLastStepDialogData.set(dialogData);
    this.dialogService.openTokenEnrollmentLastStepDialog({
      data: dialogData
    });
  }

  // TODO: Get custom path from pi.cfg
  customizationPath = "/static/public/customize/";

  readonly preTopHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "token-enrollment.wizard.pre.top.html", {
      responseType: "text"
    })
    .pipe(
      map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.bypassSecurityTrustHtml(raw)
      }))
    );
  readonly preBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "token-enrollment.wizard.pre.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor() {
    super();
  }
}
