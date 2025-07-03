import { Component, Renderer2, Version } from '@angular/core';
import { TokenEnrollmentComponent } from './token-enrollment.component';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatOption, MatSelect } from '@angular/material/select';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { EnrollHotpComponent } from './enroll-hotp/enroll-hotp.component';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { EnrollTotpComponent } from './enroll-totp/enroll-totp.component';
import { EnrollSpassComponent } from './enroll-spass/enroll-spass.component';
import { EnrollMotpComponent } from './enroll-motp/enroll-motp.component';
import { NgClass } from '@angular/common';
import { EnrollSshkeyComponent } from './enroll-sshkey/enroll-sshkey.component';
import { EnrollYubikeyComponent } from './enroll-yubikey/enroll-yubikey.component';
import { EnrollRemoteComponent } from './enroll-remote/enroll-remote.component';
import { EnrollYubicoComponent } from './enroll-yubico/enroll-yubico.component';
import { EnrollRadiusComponent } from './enroll-radius/enroll-radius.component';
import { EnrollSmsComponent } from './enroll-sms/enroll-sms.component';
import { EnrollFoureyesComponent } from './enroll-foureyes/enroll-foureyes.component';
import { EnrollApplspecComponent } from './enroll-asp/enroll-applspec.component';
import { EnrollDaypasswordComponent } from './enroll-daypassword/enroll-daypassword.component';
import { EnrollCertificateComponent } from './enroll-certificate/enroll-certificate.component';
import { EnrollEmailComponent } from './enroll-email/enroll-email.component';
import { EnrollIndexedsecretComponent } from './enroll-indexsecret/enroll-indexedsecret.component';
import { EnrollPaperComponent } from './enroll-paper/enroll-paper.component';
import { EnrollPushComponent } from './enroll-push/enroll-push.component';
import { EnrollQuestionComponent } from './enroll-questionnaire/enroll-question.component';
import { EnrollRegistrationComponent } from './enroll-registration/enroll-registration.component';
import { EnrollTanComponent } from './enroll-tan/enroll-tan.component';
import { EnrollTiqrComponent } from './enroll-tiqr/enroll-tiqr.component';
import { EnrollU2fComponent } from './enroll-u2f/enroll-u2f.component';
import { EnrollVascoComponent } from './enroll-vasco/enroll-vasco.component';
import { EnrollWebauthnComponent } from './enroll-webauthn/enroll-webauthn.component';
import { EnrollPasskeyComponent } from './enroll-passkey/enroll-passkey.component';
import { ContainerService } from '../../../services/container/container.service';
import { RealmService } from '../../../services/realm/realm.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { UserService } from '../../../services/user/user.service';
import { TokenService } from '../../../services/token/token.service';
import { ContentService } from '../../../services/content/content.service';
import { DialogService } from '../../../services/dialog/dialog.service';
import { VersionService } from '../../../services/version/version.service';
import { AuthService } from '../../../services/auth/auth.service';
import { MatTooltip } from '@angular/material/tooltip';

@Component({
  selector: 'app-token-enrollment-self-service',
  imports: [
    MatFormField,
    MatSelect,
    MatOption,
    ReactiveFormsModule,
    FormsModule,
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
    MatError,
    MatTooltip,
  ],
  templateUrl: './token-enrollment.self-service.component.html',
  styleUrl: './token-enrollment.component.scss',
})
export class TokenEnrollmentSelfServiceComponent extends TokenEnrollmentComponent {
  constructor(
    containerService: ContainerService,
    realmService: RealmService,
    notificationService: NotificationService,
    userService: UserService,
    tokenService: TokenService,
    versionService: VersionService,
    contentService: ContentService,
    dialogService: DialogService,
    renderer: Renderer2,
    private authService: AuthService,
  ) {
    super(
      containerService,
      realmService,
      notificationService,
      userService,
      tokenService,
      versionService,
      contentService,
      dialogService,
      renderer,
    );
  }

  override ngOnInit(): void {
    console.log('Initializing enrollment form in self-service');
    super.ngOnInit();
    this.selectedUserRealmControl.setValue(this.authService.realm());
    this.userFilterControl.setValue(this.authService.user());
  }

  override resetForm(): void {
    console.log('Resetting enrollment form in self-service');
    super.resetForm();
    console.log('Resetting user realm and filter controls');

    this.selectedUserRealmControl.setValue(this.authService.realm());
    this.userFilterControl.setValue(this.authService.user());
  }
}
