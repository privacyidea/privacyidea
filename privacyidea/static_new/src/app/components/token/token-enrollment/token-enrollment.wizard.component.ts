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
import { Component, inject, Renderer2 } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatNativeDateModule } from "@angular/material/core";
import { MatDatepickerModule } from "@angular/material/datepicker";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { EnrollmentResponse } from "../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
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

@Component({
  selector: "app-token-enrollment-wizard",
  imports: [
    MatFormField,
    MatSelect,
    MatOption,
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    EnrollHotpComponent,
    MatInput,
    MatLabel,
    MatAutocomplete,
    MatAutocompleteTrigger,
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
    MatError,
    MatTooltip,
    ScrollToTopDirective,
    ClearableInputComponent
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
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);
  protected override readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected override readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly preTopHtml$ = this.http
    .get("/customize/token-enrollment.wizard.pre.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly preBottomHtml$ = this.http
    .get("/customize/token-enrollment.wizard.pre.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(renderer: Renderer2) {
    super(renderer);
  }

  protected override openLastStepDialog(args: { response: EnrollmentResponse; user: UserData | null }) {
    const { response, user } = args;
    this.dialogService.openTokenEnrollmentLastStepDialog({
      data: {
        response,
        enrollToken: this.enrollToken.bind(this),
        user: user,
        userRealm: this.userService.selectedUserRealm(),
        onlyAddToRealm: this.onlyAddToRealmControl.value
      }
    });
  }
}
