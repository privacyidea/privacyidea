import {
  Component,
  computed,
  HostListener,
  Injectable,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
  MatSuffix,
} from '@angular/material/form-field';
import { MatOption, MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { EnrollHotpComponent } from './enroll-hotp/enroll-hotp.component';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { ContainerService } from '../../../services/container/container.service';
import { RealmService } from '../../../services/realm/realm.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { UserService } from '../../../services/user/user.service';
import {
  DateAdapter,
  MAT_DATE_FORMATS,
  MatNativeDateModule,
  NativeDateAdapter,
  provideNativeDateAdapter,
} from '@angular/material/core';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import {
  EnrollmentResponse,
  TokenDetails,
  TokenService,
} from '../../../services/token/token.service';
import { EnrollTotpComponent } from './enroll-totp/enroll-totp.component';
import { MatDialog } from '@angular/material/dialog';
import { TokenEnrollmentFirstStepDialogComponent } from './token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';
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
import { VersionService } from '../../../services/version/version.service';
import { TokenEnrollmentSecondStepDialogComponent } from './token-enrollment-second-step-dialog/token-enrollment-second-step-dialog.component';
import { ContentService } from '../../../services/content/content.service';
import { PiResponse } from '../../../app.component';

export const CUSTOM_DATE_FORMATS = {
  parse: { dateInput: 'YYYY-MM-DD' },
  display: {
    dateInput: 'YYYY-MM-DD',
    monthYearLabel: 'MMM YYYY',
    dateA11yLabel: 'LL',
    monthYearA11yLabel: 'MMMM YYYY',
  },
};

export const TIMEZONE_OFFSETS = (() => {
  const offsets = [];
  for (let i = -12; i <= 14; i++) {
    const sign = i < 0 ? '-' : '+';
    const absOffset = Math.abs(i);
    const hours = String(absOffset).padStart(2, '0');
    const label = `UTC${sign}${hours}:00`;
    const value = `${sign}${hours}:00`;
    offsets.push({ label, value });
  }
  return offsets;
})();

@Injectable()
export class CustomDateAdapter extends NativeDateAdapter {
  private timezoneOffset = '+00:00';

  override format(date: Date): string {
    const adjustedDate = this._applyTimezoneOffset(date);
    const year = adjustedDate.getFullYear();
    const month = (adjustedDate.getMonth() + 1).toString().padStart(2, '0');
    const day = adjustedDate.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private _applyTimezoneOffset(date: Date): Date {
    const offsetParts = this.timezoneOffset.split(':').map(Number);
    const offsetMinutes = offsetParts[0] * 60 + (offsetParts[1] || 0);
    const adjustedTime = date.getTime() + offsetMinutes * 60 * 1000;
    return new Date(adjustedTime);
  }
}

@Component({
  selector: 'app-token-enrollment',
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
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    MatNativeDateModule,
    MatDatepickerModule,
    MatSuffix,
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
    MatError,
    EnrollPasskeyComponent,
  ],
  providers: [
    provideNativeDateAdapter(),
    { provide: DateAdapter, useFactory: () => new CustomDateAdapter('+00:00') },
    { provide: MAT_DATE_FORMATS, useValue: CUSTOM_DATE_FORMATS },
  ],
  templateUrl: './token-enrollment.component.html',
  styleUrls: ['./token-enrollment.component.scss'],
  standalone: true,
})
export class TokenEnrollmentComponent {
  timezoneOptions = TIMEZONE_OFFSETS;
  tokenSerial = this.tokenService.tokenSerial;
  containerSerial = this.containerService.containerSerial;
  selectedContent = this.contentService.selectedContent;
  tokenTypeOptions = this.tokenService.tokenTypeOptions;
  selectedTokenType = this.tokenService.selectedTokenType;
  testYubiKey = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  otpLength = linkedSignal({
    source: this.testYubiKey,
    computation: (testYubiKey) => {
      if (testYubiKey.length > 0) {
        return testYubiKey.length;
      } else {
        return this.selectedTokenType().key === 'yubikey' ? 44 : 6;
      }
    },
  });
  otpKey = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  sshPublicKey = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  description = linkedSignal({
    source: () => ({
      sshPublicKey: this.sshPublicKey(),
      selectedType: this.selectedTokenType(),
    }),
    computation: (source: any) => {
      const parts = source.sshPublicKey?.split(' ') ?? [];
      return parts.length >= 3 ? parts[2] : '';
    },
  });
  generateOnServer = linkedSignal({
    source: this.selectedTokenType,
    computation: () => true,
  });
  selectedTimezoneOffset = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '+01:00',
  });
  selectedStartTime = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  selectedEndTime = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  selectedStartDate = linkedSignal({
    source: this.selectedTokenType,
    computation: () => new Date(),
  });
  selectedEndDate = linkedSignal({
    source: this.selectedTokenType,
    computation: () => new Date(),
  });
  timeStep = linkedSignal({
    source: this.selectedTokenType,
    computation: () => 30,
  });
  enrollResponse: WritableSignal<EnrollmentResponse | null> = linkedSignal({
    source: this.selectedTokenType,
    computation: () => null,
  });
  pollResponse: WritableSignal<any> = linkedSignal({
    source: this.selectedTokenType,
    computation: () => null,
  });
  motpPin = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  repeatMotpPin = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  checkPinLocally = linkedSignal({
    source: this.selectedTokenType,
    computation: () => false,
  });
  remoteServer = linkedSignal({
    source: this.selectedTokenType,
    computation: () => ({ url: '', id: '' }),
  });
  remoteSerial = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  remoteUser = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  remoteRealm = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  remoteResolver = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  yubikeyIdentifier = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  radiusServerConfiguration = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  radiusUser = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  readNumberDynamically = linkedSignal({
    source: this.selectedTokenType,
    computation: () => false,
  });
  smsGateway = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  phoneNumber = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  separator = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  requiredTokenOfRealms = linkedSignal({
    source: this.selectedTokenType,
    computation: () => [] as { realm: string; tokens: number }[],
  });
  serviceId = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  caConnector = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  certTemplate = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  pem = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  emailAddress = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  readEmailDynamically = linkedSignal({
    source: this.selectedTokenType,
    computation: () => false,
  });
  answers = linkedSignal({
    source: this.selectedTokenType,
    computation: () => ({}) as Record<string, string>,
  });
  useVascoSerial = linkedSignal({
    source: this.selectedTokenType,
    computation: () => false,
  });
  vascoSerial = linkedSignal({
    source: this.otpKey,
    computation: (otpKey) => {
      if (this.selectedTokenType().key === 'vasco' && this.useVascoSerial()) {
        return EnrollVascoComponent.convertOtpKeyToVascoSerial(otpKey);
      }
      return '';
    },
  });
  onlyAddToRealm = linkedSignal({
    source: this.selectedTokenType,
    computation: () => false,
  });
  setPinValue = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  repeatPinValue = linkedSignal({
    source: this.selectedTokenType,
    computation: () => '',
  });
  hashAlgorithm = linkedSignal({
    source: this.selectedTokenType,
    computation: () => 'sha1',
  });
  enrollmentOptions = computed(() => {
    return {
      type: this.selectedTokenType().key,
      description: this.description(),
      container_serial: this.containerService.selectedContainer().trim(),
      validity_period_start: this.formatDateTimeOffset(
        this.selectedStartDate(),
        this.selectedStartTime(),
        this.selectedTimezoneOffset(),
      ),
      validity_period_end: this.formatDateTimeOffset(
        this.selectedEndDate(),
        this.selectedEndTime(),
        this.selectedTimezoneOffset(),
      ),
      user: this.userService.selectedUsername().trim(),
      pin: this.setPinValue(),

      // hotp, totp, motp, applspec
      generateOnServer: this.generateOnServer(),
      otpLength: this.otpLength(),
      otpKey: this.otpKey(),
      hashAlgorithm: this.hashAlgorithm(),
      timeStep: this.timeStep(),

      // motp
      motpPin: this.motpPin(),

      // sshkey
      sshPublicKey: this.sshPublicKey(),

      // remote
      remoteServer: this.remoteServer(),
      remoteSerial: this.remoteSerial(),
      remoteUser: this.remoteUser().trim(),
      remoteRealm: this.remoteRealm().trim(),
      remoteResolver: this.remoteResolver().trim(),
      checkPinLocally: this.checkPinLocally(),

      // yubico
      yubicoIdentifier: this.yubikeyIdentifier(),

      // radius
      radiusServerConfiguration: this.radiusServerConfiguration(),
      radiusUser: this.radiusUser().trim(),

      // sms
      smsGateway: this.smsGateway(),
      phoneNumber: this.phoneNumber(),

      // 4eyes
      separator: this.separator(),
      requiredTokenOfRealms: this.requiredTokenOfRealms(),
      onlyAddToRealm: this.onlyAddToRealm(),
      userRealm: this.userService.selectedUserRealm(),

      // applspec
      serviceId: this.serviceId(),

      // certificate
      caConnector: this.caConnector(),
      certTemplate: this.certTemplate(),
      pem: this.pem(),

      // email
      emailAddress: this.emailAddress().trim(),
      readEmailDynamically: this.readEmailDynamically(),

      // question
      answers: this.answers(),

      // vasco
      vascoSerial: this.vascoSerial(),
      useVascoSerial: this.useVascoSerial(),
    };
  });
  @ViewChild(EnrollPasskeyComponent)
  enrollPasskeyComponent!: EnrollPasskeyComponent;
  @ViewChild(EnrollWebauthnComponent)
  enrollWebauthnComponent!: EnrollWebauthnComponent;

  constructor(
    protected containerService: ContainerService,
    protected realmService: RealmService,
    private notificationService: NotificationService,
    protected userService: UserService,
    protected tokenService: TokenService,
    protected firstDialog: MatDialog,
    protected secondDialog: MatDialog,
    protected versioningService: VersionService,
    private contentService: ContentService,
  ) {}

  @HostListener('document:keydown.enter', ['$event'])
  onEnter(event: KeyboardEvent) {
    const target = event.target as HTMLElement;

    if (target.tagName === 'TEXTAREA') {
      return;
    }
    if (
      this.firstDialog.openDialogs.length === 0 &&
      this.secondDialog.openDialogs.length === 0
    ) {
      this.enrollToken();
    }
  }

  formatDateTimeOffset(date: Date, time: string, offset: string): string {
    const timeMatch = time.match(/^(\d{2}):(\d{2})$/);
    if (!timeMatch) {
      return '';
    }
    const hours = parseInt(timeMatch[1], 10);
    const minutes = parseInt(timeMatch[2], 10);
    const newDate = new Date(date.getTime());

    newDate.setHours(hours, minutes, 0, 0);

    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, '0');
    const day = String(newDate.getDate()).padStart(2, '0');
    const formattedHours = String(newDate.getHours()).padStart(2, '0');
    const formattedMinutes = String(newDate.getMinutes()).padStart(2, '0');
    const offsetNoColon = offset.replace(':', '');

    return `${year}-${month}-${day}T${formattedHours}:${formattedMinutes}${offsetNoColon}`;
  }

  enrollToken(): void {
    this.pollResponse.set(null);
    this.enrollResponse.set(null);
    this.tokenService.enrollToken(this.enrollmentOptions()).subscribe({
      next: (response) => {
        this.enrollResponse.set(response);
        this.handleEnrollmentResponse(response);
      },
      error: (error) => {
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to enroll token. ' + message,
        );
      },
    });
  }

  reopenEnrollmentDialog() {
    const enrollResponse = this.enrollResponse();
    let waitingForClient =
      ((enrollResponse?.detail?.rollout_state === 'clientwait' ||
        enrollResponse?.detail?.passkey_registration ||
        enrollResponse?.detail?.webAuthnRegisterRequest) &&
        !this.pollResponse()) ||
      this.pollResponse()?.result?.value?.tokens[0]?.rollout_state ===
        'clientwait';
    if (waitingForClient) {
      this.openFirstStepDialog(enrollResponse!);
      this.pollTokenRolloutState(enrollResponse!.detail?.serial, 2000);
    } else {
      this.openSecondStepDialog(enrollResponse);
    }
  }

  userIsRequired() {
    return ['tiqr', 'webauthn', 'passkey', 'certificate'].includes(
      this.selectedTokenType().key,
    );
  }

  protected openSecondStepDialog(response: any) {
    this.secondDialog.open(TokenEnrollmentSecondStepDialogComponent, {
      data: {
        response: response,
        enrollToken: this.enrollToken.bind(this),
        username: this.userService.selectedUsername(),
        userRealm: this.userService.selectedUserRealm(),
        onlyAddToRealm: this.onlyAddToRealm(),
      },
    });
  }

  private handleEnrollmentResponse(response: EnrollmentResponse): void {
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState !== 'clientwait') {
      this.notificationService.openSnackBar(
        `Token ${detail.serial} enrolled successfully.`,
      );
    }

    switch (this.selectedTokenType().key) {
      case 'webauthn':
        this.openFirstStepDialog(response);
        this.enrollWebauthnComponent.registerWebauthn(detail).subscribe({
          next: () => {
            this.pollTokenRolloutState(detail.serial, 2000);
          },
        });
        break;
      case 'passkey':
        this.openFirstStepDialog(response);
        this.enrollPasskeyComponent.registerPasskey(detail).subscribe({
          next: () => {
            this.pollTokenRolloutState(detail.serial, 2000);
          },
        });
        break;
      case 'push':
        this.openFirstStepDialog(response);
        this.pollTokenRolloutState(detail.serial, 5000);
        break;
      default:
        this.openSecondStepDialog(response);
        break;
    }
  }

  private openFirstStepDialog(response: EnrollmentResponse) {
    this.firstDialog.open(TokenEnrollmentFirstStepDialogComponent, {
      data: {
        response: response,
      },
    });
  }

  private pollTokenRolloutState(tokenSerial: string, startTime: number) {
    return this.tokenService
      .pollTokenRolloutState(tokenSerial, startTime)
      .subscribe({
        next: (pollResponse) => {
          this.pollResponse.set(pollResponse);
          if (
            pollResponse.result?.value?.tokens[0].rollout_state !== 'clientwait'
          ) {
            this.firstDialog.closeAll();
            this.openSecondStepDialog(this.enrollResponse());
            this.notificationService.openSnackBar(
              `Token ${tokenSerial} enrolled successfully.`,
            );
          }
        },
      });
  }
}
