import { AsyncPipe, NgClass } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Inject, Renderer2 } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatOption, MatSelect } from '@angular/material/select';
import { DomSanitizer } from '@angular/platform-browser';
import { map } from 'rxjs';
import { EnrollmentResponse } from '../../../mappers/token-api-payload/_token-api-payload.mapper';
import { ContainerService } from '../../../services/container/container.service';
import { ContentService } from '../../../services/content/content.service';
import { DialogService } from '../../../services/dialog/dialog.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { RealmService } from '../../../services/realm/realm.service';
import { TokenService } from '../../../services/token/token.service';
import { UserData, UserService } from '../../../services/user/user.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../services/version/version.service';
import { EnrollApplspecComponent } from './enroll-asp/enroll-applspec.component';
import { EnrollCertificateComponent } from './enroll-certificate/enroll-certificate.component';
import { EnrollDaypasswordComponent } from './enroll-daypassword/enroll-daypassword.component';
import { EnrollEmailComponent } from './enroll-email/enroll-email.component';
import { EnrollFoureyesComponent } from './enroll-foureyes/enroll-foureyes.component';
import { EnrollHotpComponent } from './enroll-hotp/enroll-hotp.component';
import { EnrollIndexedsecretComponent } from './enroll-indexsecret/enroll-indexedsecret.component';
import { EnrollMotpComponent } from './enroll-motp/enroll-motp.component';
import { EnrollPaperComponent } from './enroll-paper/enroll-paper.component';
import { EnrollPasskeyComponent } from './enroll-passkey/enroll-passkey.component';
import { EnrollPushComponent } from './enroll-push/enroll-push.component';
import { EnrollQuestionComponent } from './enroll-questionnaire/enroll-question.component';
import { EnrollRadiusComponent } from './enroll-radius/enroll-radius.component';
import { EnrollRegistrationComponent } from './enroll-registration/enroll-registration.component';
import { EnrollRemoteComponent } from './enroll-remote/enroll-remote.component';
import { EnrollSmsComponent } from './enroll-sms/enroll-sms.component';
import { EnrollSpassComponent } from './enroll-spass/enroll-spass.component';
import { EnrollSshkeyComponent } from './enroll-sshkey/enroll-sshkey.component';
import { EnrollTanComponent } from './enroll-tan/enroll-tan.component';
import { EnrollTiqrComponent } from './enroll-tiqr/enroll-tiqr.component';
import { EnrollTotpComponent } from './enroll-totp/enroll-totp.component';
import { EnrollU2fComponent } from './enroll-u2f/enroll-u2f.component';
import { EnrollVascoComponent } from './enroll-vasco/enroll-vasco.component';
import { EnrollWebauthnComponent } from './enroll-webauthn/enroll-webauthn.component';
import { EnrollYubicoComponent } from './enroll-yubico/enroll-yubico.component';
import { EnrollYubikeyComponent } from './enroll-yubikey/enroll-yubikey.component';
import { TokenEnrollmentComponent } from './token-enrollment.component';

@Component({
  selector: 'app-token-enrollment-wizard',
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
  ],
  templateUrl: './token-enrollment.wizard.component.html',
  styleUrl: './token-enrollment.component.scss',
})
export class TokenEnrollmentWizardComponent extends TokenEnrollmentComponent {
  readonly preTopHtml$ = this.http
    .get('/customize/token-enrollment.wizard.pre.top.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly preBottomHtml$ = this.http
    .get('/customize/token-enrollment.wizard.pre.bottom.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    containerService: ContainerService,
    realmService: RealmService,
    notificationService: NotificationService,
    userService: UserService,
    tokenService: TokenService,
    contentService: ContentService,
    @Inject(VersioningService)
    versioningService: VersioningServiceInterface,
    dialogService: DialogService,
    renderer: Renderer2,
  ) {
    super(
      containerService,
      realmService,
      notificationService,
      userService,
      tokenService,
      versioningService,
      contentService,
      dialogService,
      renderer,
    );
  }

  protected override openLastStepDialog(args: {
    response: EnrollmentResponse;
    user: UserData | null;
  }) {
    const { response, user } = args;
    this.dialogService.openTokenEnrollmentLastStepDialog({
      data: {
        response,
        enrollToken: this.enrollToken.bind(this),
        user: user,
        userRealm: this.userService.selectedUserRealm(),
        onlyAddToRealm: this.onlyAddToRealm(),
      },
    });
  }
}
