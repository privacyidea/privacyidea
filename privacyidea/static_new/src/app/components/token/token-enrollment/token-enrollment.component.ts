import {
  Component,
  computed,
  effect,
  Injectable,
  Input,
  linkedSignal,
  signal,
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
import { TokenComponent, TokenSelectedContent } from '../token.component';
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
  EnrollmentOptions,
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
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { distinctUntilChanged, from, switchMap } from 'rxjs';
import { map } from 'rxjs/operators';
import { TokenEnrollmentSecondStepDialogComponent } from './token-enrollment-second-step-dialog/token-enrollment-second-step-dialog.component';

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

  override format(date: Date, displayFormat: any): string {
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
  tokenTypesOptions = TokenComponent.tokenTypes;
  timezoneOptions = TIMEZONE_OFFSETS;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  selectedType = signal(this.tokenTypesOptions[0]);
  setPinValue = signal('');
  repeatPinValue = signal('');
  selectedUserRealm = signal('');
  selectedUsername = signal('');
  selectedContainer = signal<string>('');
  containerOptions = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  generateOnServer = signal(true);
  testYubiKey = signal('');
  otpKey = signal('');
  hashAlgorithm = signal('sha1');
  sshPublicKey = signal('');
  selectedTimezoneOffset = signal('+01:00');
  selectedStartTime = signal('');
  selectedEndTime = signal('');
  selectedStartDate = signal(new Date());
  selectedEndDate = signal(new Date());
  timeStep = signal(30);
  response: WritableSignal<any> = signal(null);
  regenerateToken = signal(false);
  motpPin = signal('');
  repeatMotpPin = signal('');
  checkPinLocally = signal(false);
  remoteServer = signal({ url: '', id: '' });
  remoteSerial = signal('');
  remoteUser = signal('');
  remoteRealm = signal('');
  remoteResolver = signal('');
  yubikeyIdentifier = signal('');
  radiusServerConfiguration = signal('');
  radiusUser = signal('');
  readNumberDynamically = signal(false);
  smsGateway = signal('');
  phoneNumber = signal('');
  separator = signal('');
  requiredTokenOfRealm = signal<{ realm: string; tokens: number }[]>([]);
  serviceId = signal('');
  caConnector = signal('');
  certTemplate = signal('');
  pem = signal('');
  emailAddress = signal('');
  readEmailDynamically = signal(false);
  answers = signal<Record<string, string>>({});
  useVascoSerial = signal(false);
  onlyAddToRealm = signal(false);
  otpLength = linkedSignal({
    source: this.testYubiKey,
    computation: (testYubiKey) => {
      if (testYubiKey.length > 0) {
        return testYubiKey.length;
      } else {
        return this.selectedType() ===
          this.tokenTypesOptions.find((type) => type.key === 'yubikey')
          ? 44
          : 6;
      }
    },
  });
  description = linkedSignal({
    source: this.sshPublicKey,
    computation: (sshPublicKey) => {
      const parts = sshPublicKey?.split(' ') ?? [];
      return parts.length >= 3 ? parts[2] : '';
    },
  });
  vascoSerial = linkedSignal({
    source: this.otpKey,
    computation: (otpKey) => {
      if (this.useVascoSerial()) {
        return EnrollVascoComponent.convertOtpKeyToVascoSerial(otpKey);
      }
      return '';
    },
  });
  filteredContainerOptions = computed(() => {
    const filter = (this.selectedContainer() || '').toLowerCase();
    return this.containerOptions().filter((option) =>
      option.toLowerCase().includes(filter),
    );
  });
  fetchedUsernames = toSignal(
    toObservable(this.selectedUserRealm).pipe(
      distinctUntilChanged(),
      switchMap((realm) => {
        if (!realm) {
          return from<string[]>([]);
        }
        return this.userService
          .getUsers(realm)
          .pipe(
            map((result: any) =>
              result.value.map((user: any) => user.username),
            ),
          );
      }),
    ),
    { initialValue: [] },
  );
  userOptions = computed(() => this.fetchedUsernames());
  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });
  @ViewChild(EnrollPasskeyComponent)
  enrollPasskeyComponent!: EnrollPasskeyComponent;
  @ViewChild(EnrollWebauthnComponent)
  enrollWebauthnComponent!: EnrollWebauthnComponent;
  protected readonly TokenEnrollmentDialogComponent =
    TokenEnrollmentFirstStepDialogComponent;

  constructor(
    private containerService: ContainerService,
    private realmService: RealmService,
    private notificationService: NotificationService,
    private userService: UserService,
    private tokenService: TokenService,
    protected firstDialog: MatDialog,
    protected secondDialog: MatDialog,
    protected versioningService: VersionService,
  ) {
    const resetEnrollmentOptions = () => {
      this.realmService.getDefaultRealm().subscribe({
        next: (realm: any) => {
          this.selectedUserRealm.set(realm);
        },
      });
      this.getRealmOptions();
      this.response.set(null);
      this.tokenSerial.set('');
      this.description.set('');
      this.setPinValue.set('');
      this.repeatPinValue.set('');
      this.selectedUsername.set('');
      this.selectedContainer.set('');
      this.generateOnServer.set(true);
      this.otpLength.set(6);
      this.otpKey.set('');
      this.hashAlgorithm.set('sha1');
      this.selectedTimezoneOffset.set('+01:00');
      this.selectedStartTime.set('');
      this.selectedEndTime.set('');
      this.selectedStartDate.set(new Date());
      this.selectedEndDate.set(new Date());
      this.timeStep.set(30);
      this.regenerateToken.set(false);
      this.motpPin.set('');
      this.repeatMotpPin.set('');
      this.sshPublicKey.set('');
      this.checkPinLocally.set(false);
      this.remoteServer.set({ url: '', id: '' });
      this.remoteSerial.set('');
      this.remoteUser.set('');
      this.remoteRealm.set('');
      this.remoteResolver.set('');
      this.yubikeyIdentifier.set('');
      this.radiusServerConfiguration.set('');
      this.radiusUser.set('');
      this.readNumberDynamically.set(false);
      this.smsGateway.set('');
      this.phoneNumber.set('');
      this.separator.set('');
      this.requiredTokenOfRealm.set([]);
      this.serviceId.set('');
      this.caConnector.set('');
      this.certTemplate.set('');
      this.pem.set('');
      this.emailAddress.set('');
      this.readEmailDynamically.set(false);
      this.answers.set({});
      this.vascoSerial.set('');
      this.useVascoSerial.set(false);
      this.onlyAddToRealm.set(false);
    };

    effect(() => {
      this.selectedType();
      resetEnrollmentOptions();
    });

    effect(() => {
      if (this.regenerateToken()) {
        this.enrollToken();
      }
    });
  }

  ngAfterViewInit() {
    this.getContainerOptions();
    this.selectedContainer.set(this.containerSerial());
  }

  getRealmOptions() {
    this.realmService.getRealms().subscribe({
      next: (realms: any) => {
        this.realmOptions.set(Object.keys(realms.result.value));
      },
    });
  }

  getContainerOptions() {
    this.containerService.getContainerData({ noToken: true }).subscribe({
      next: (containers: any) => {
        this.containerOptions.set(
          Object.values(
            containers.result.value.containers as {
              serial: string;
            }[],
          ).map((container) => container.serial),
        );
      },
    });
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

  enrollToken() {
    const enrollmentOptions: EnrollmentOptions = {
      type: this.selectedType().key,
      generateOnServer: this.generateOnServer(),
      otpLength: this.otpLength(),
      otpKey: this.otpKey(),
      hashAlgorithm: this.hashAlgorithm(),
      timeStep: this.timeStep(),
      description: this.description(),
      tokenSerial: this.tokenSerial(),
      user: this.selectedUsername().trim(),
      container_serial: this.selectedContainer().trim(),
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
      pin: this.setPinValue(),
      motpPin: this.motpPin(),
      sshPublicKey: this.sshPublicKey(),
      remoteServer: this.remoteServer(),
      remoteSerial: this.remoteSerial(),
      remoteUser: this.remoteUser().trim(),
      remoteRealm: this.remoteRealm().trim(),
      remoteResolver: this.remoteResolver().trim(),
      checkPinLocally: this.checkPinLocally(),
      yubicoIdentifier: this.yubikeyIdentifier(),
      radiusServerConfiguration: this.radiusServerConfiguration(),
      radiusUser: this.radiusUser().trim(),
      smsGateway: this.smsGateway(),
      phoneNumber: this.phoneNumber(),
      separator: this.separator(),
      requiredTokenOfRealms: this.requiredTokenOfRealm(),
      serviceId: this.serviceId(),
      caConnector: this.caConnector(),
      certTemplate: this.certTemplate(),
      pem: this.pem(),
      emailAddress: this.emailAddress().trim(),
      readEmailDynamically: this.readEmailDynamically(),
      answers: this.answers(),
      vascoSerial: this.vascoSerial(),
      useVascoSerial: this.useVascoSerial(),
      onlyAddToRealm: this.onlyAddToRealm(),
      userRealm: this.selectedUserRealm(),
    };
    this.tokenService.enrollToken(enrollmentOptions).subscribe({
      next: (response: any) => {
        if (
          !this.regenerateToken() &&
          response.detail.rollout_state !== 'clientwait'
        ) {
          this.notificationService.openSnackBar(
            `Token ${response.detail.serial} enrolled successfully.`,
          );
        }
        this.tokenSerial.set(response.detail.serial);
        if (response.detail.webAuthnRegisterRequest) {
          this.openFirstStepDialog(response);
          this.enrollWebauthnComponent
            .registerWebauthn(response.detail)
            .subscribe({
              next: () => {
                this.firstDialog.closeAll();
                this.openSecondStepDialog(response);
              },
            });
        } else if (response.detail.passkey_registration) {
          this.openFirstStepDialog(response);
          this.enrollPasskeyComponent
            .registerPasskey(response.detail, this.firstDialog)
            .subscribe({
              next: () => {
                this.firstDialog.closeAll();
                this.openSecondStepDialog(response);
              },
            });
        } else if (response.detail.rollout_state === 'clientwait') {
          this.openFirstStepDialog(response);
          this.pollTokenEnrollment(response.detail.serial, 5000);
        } else {
          this.response.set(response);
          this.openSecondStepDialog(response);
          if (this.regenerateToken()) {
            this.regenerateToken.set(false);
          }
        }
      },
    });
  }

  reopenEnrollmentDialog() {
    this.openSecondStepDialog(this.response());
    if (this.response().detail.rollout_state === 'clientwait') {
      this.pollTokenEnrollment(this.tokenSerial(), 2000);
    }
  }

  userIsRequired() {
    return ['tiqr', 'webauthn', 'passkey', 'certificate'].includes(
      this.selectedType().key,
    );
  }

  private openFirstStepDialog(response: any) {
    this.firstDialog.open(TokenEnrollmentFirstStepDialogComponent, {
      data: {
        response: response,
        tokenSerial: this.tokenSerial,
        containerSerial: this.containerSerial,
        selectedContent: this.selectedContent,
        regenerateToken: this.regenerateToken,
        isProgrammaticChange: this.isProgrammaticChange,
        username: this.selectedUsername(),
        userRealm: this.selectedUserRealm(),
        onlyAddToRealm: this.onlyAddToRealm(),
      },
    });
  }

  private openSecondStepDialog(response: any) {
    this.secondDialog.open(TokenEnrollmentSecondStepDialogComponent, {
      data: {
        response: response,
        tokenSerial: this.tokenSerial,
        containerSerial: this.containerSerial,
        selectedContent: this.selectedContent,
        regenerateToken: this.regenerateToken,
        isProgrammaticChange: this.isProgrammaticChange,
        username: this.selectedUsername(),
        userRealm: this.selectedUserRealm(),
        onlyAddToRealm: this.onlyAddToRealm(),
      },
    });
  }

  private pollTokenEnrollment(tokenSerial: string, startTime: number): void {
    this.tokenService.pollTokenState(tokenSerial, startTime).subscribe({
      next: (pollResponse: any) => {
        this.response.set(pollResponse);
        if (
          this.response().result.value.tokens[0].rollout_state === 'enrolled'
        ) {
          this.firstDialog.closeAll();
          this.notificationService.openSnackBar(
            `Token ${tokenSerial} enrolled successfully.`,
          );
        }
      },
    });
  }
}
