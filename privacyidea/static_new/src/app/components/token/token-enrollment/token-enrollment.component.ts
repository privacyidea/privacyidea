import {
  Component,
  computed,
  effect,
  Injectable,
  Input,
  linkedSignal,
  signal,
  untracked,
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
import { TokenService } from '../../../services/token/token.service';
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
  tokenTypesOptions = TokenComponent.tokenTypeOptions;
  timezoneOptions = TIMEZONE_OFFSETS;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  selectedType = signal(this.tokenTypesOptions[0]);
  selectedUserRealm = signal('');
  containerOptions = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  private readonly defaults = {
    testYubiKey: '',
    otpKey: '',
    sshPublicKey: '',
    generateOnServer: true,
    selectedUsername: '',
    selectedContainer: '',
    selectedTimezoneOffset: '+01:00',
    selectedStartTime: '',
    selectedEndTime: '',
    selectedStartDate: new Date(),
    selectedEndDate: new Date(),
    timeStep: 30,
    response: null as any,
    regenerateToken: false,
    motpPin: '',
    repeatMotpPin: '',
    checkPinLocally: false,
    remoteServer: { url: '', id: '' },
    remoteSerial: '',
    remoteUser: '',
    remoteRealm: '',
    remoteResolver: '',
    yubikeyIdentifier: '',
    radiusServerConfiguration: '',
    radiusUser: '',
    readNumberDynamically: false,
    smsGateway: '',
    phoneNumber: '',
    separator: '',
    requiredTokenOfRealms: [] as { realm: string; tokens: number }[],
    serviceId: '',
    caConnector: '',
    certTemplate: '',
    pem: '',
    emailAddress: '',
    readEmailDynamically: false,
    answers: {} as Record<string, string>,
    useVascoSerial: false,
    onlyAddToRealm: false,
    setPinValue: '',
    repeatPinValue: '',
    hashAlgorithm: 'sha1',
  };
  testYubiKey = signal(this.defaults.testYubiKey);
  otpKey = signal(this.defaults.otpKey);
  sshPublicKey = signal(this.defaults.sshPublicKey);
  generateOnServer = signal(this.defaults.generateOnServer);
  selectedUsername = signal(this.defaults.selectedUsername);
  selectedContainer = signal(this.defaults.selectedContainer);
  selectedTimezoneOffset = signal(this.defaults.selectedTimezoneOffset);
  selectedStartTime = signal(this.defaults.selectedStartTime);
  selectedEndTime = signal(this.defaults.selectedEndTime);
  selectedStartDate = signal(this.defaults.selectedStartDate);
  selectedEndDate = signal(this.defaults.selectedEndDate);
  timeStep = signal(this.defaults.timeStep);
  response: WritableSignal<any> = signal(this.defaults.response);
  regenerateToken = signal(this.defaults.regenerateToken);
  motpPin = signal(this.defaults.motpPin);
  repeatMotpPin = signal(this.defaults.repeatMotpPin);
  checkPinLocally = signal(this.defaults.checkPinLocally);
  remoteServer = signal(this.defaults.remoteServer);
  remoteSerial = signal(this.defaults.remoteSerial);
  remoteUser = signal(this.defaults.remoteUser);
  remoteRealm = signal(this.defaults.remoteRealm);
  remoteResolver = signal(this.defaults.remoteResolver);
  yubikeyIdentifier = signal(this.defaults.yubikeyIdentifier);
  radiusServerConfiguration = signal(this.defaults.radiusServerConfiguration);
  radiusUser = signal(this.defaults.radiusUser);
  readNumberDynamically = signal(this.defaults.readNumberDynamically);
  smsGateway = signal(this.defaults.smsGateway);
  phoneNumber = signal(this.defaults.phoneNumber);
  separator = signal(this.defaults.separator);
  requiredTokenOfRealms = signal(this.defaults.requiredTokenOfRealms);
  serviceId = signal(this.defaults.serviceId);
  caConnector = signal(this.defaults.caConnector);
  certTemplate = signal(this.defaults.certTemplate);
  pem = signal(this.defaults.pem);
  emailAddress = signal(this.defaults.emailAddress);
  readEmailDynamically = signal(this.defaults.readEmailDynamically);
  answers = signal(this.defaults.answers);
  useVascoSerial = signal(this.defaults.useVascoSerial);
  onlyAddToRealm = signal(this.defaults.onlyAddToRealm);
  setPinValue = signal(this.defaults.setPinValue);
  repeatPinValue = signal(this.defaults.repeatPinValue);
  hashAlgorithm = signal(this.defaults.hashAlgorithm);
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
  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });
  filteredContainerOptions = computed(() => {
    const filter = (this.selectedContainer() || '').toLowerCase();
    return this.containerOptions().filter((option) =>
      option.toLowerCase().includes(filter),
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
    effect(() => {
      this.selectedType();
      untracked(() => {
        this.resetEnrollmentOptions();
      });
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

  enrollToken(): void {
    const enrollmentOptions = this.buildEnrollmentOptions();

    this.tokenService.enrollToken(enrollmentOptions).subscribe({
      next: (response: any) => {
        this.response.set(response);
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
    if (this.response().detail?.rollout_state === 'clientwait') {
      this.openFirstStepDialog(this.response());
      this.pollTokenRolloutState(this.tokenSerial(), 2000);
    } else {
      this.openSecondStepDialog(this.response());
    }
  }

  userIsRequired() {
    return ['tiqr', 'webauthn', 'passkey', 'certificate'].includes(
      this.selectedType().key,
    );
  }

  private resetEnrollmentOptions = () => {
    this.realmService.getDefaultRealm().subscribe({
      next: (realm: any) => {
        this.selectedUserRealm.set(realm);
      },
    });
    this.getRealmOptions();
    Object.entries(this.defaults).forEach(([key, value]) => {
      (this as any)[key]?.set(value);
    });
  };

  private buildEnrollmentOptions() {
    return {
      type: this.selectedType().key,
      description: this.description(),
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
      user: this.selectedUsername().trim(),
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
      userRealm: this.selectedUserRealm(),

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
  }

  private handleEnrollmentResponse(response: any): void {
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    this.tokenSerial.update((s) => (detail.serial ? detail.serial : s));

    if (rolloutState !== 'clientwait') {
      this.notificationService.openSnackBar(
        `Token ${detail.serial} enrolled successfully.`,
      );
    }

    switch (this.selectedType().key) {
      case 'webauthn':
        this.openFirstStepDialog(response);
        this.enrollWebauthnComponent.registerWebauthn(detail).subscribe({
          next: () => {
            this.pollTokenRolloutState(detail.serial, 400).add(() => {
              this.firstDialog.closeAll();
              this.openSecondStepDialog(response);
            });
          },
        });
        break;
      case 'passkey':
        this.openFirstStepDialog(response);
        this.enrollPasskeyComponent.registerPasskey(detail).subscribe({
          next: () => {
            this.pollTokenRolloutState(detail.serial, 400).add(() => {
              this.firstDialog.closeAll();
              this.openSecondStepDialog(response);
            });
          },
        });
        break;
      case 'push':
        this.openFirstStepDialog(response);
        this.pollTokenRolloutState(detail.serial, 5000).add(() => {
          this.firstDialog.closeAll();
          this.openSecondStepDialog(response);
        });
        break;
      default:
        this.openSecondStepDialog(response);
        break;
    }
    this.regenerateToken.set(false);
  }

  private openFirstStepDialog(response: any) {
    this.firstDialog.open(TokenEnrollmentFirstStepDialogComponent, {
      data: {
        response: response,
        tokenSerial: this.tokenSerial,
        containerSerial: this.containerSerial,
        selectedContent: this.selectedContent,
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

  private pollTokenRolloutState(tokenSerial: string, startTime: number) {
    return this.tokenService
      .pollTokenRolloutState(tokenSerial, startTime)
      .subscribe({
        next: (pollResponse: any) => {
          if (
            pollResponse.result.value.tokens[0].rollout_state === 'enrolled'
          ) {
            this.notificationService.openSnackBar(
              `Token ${tokenSerial} enrolled successfully.`,
            );
          }
        },
      });
  }
}
