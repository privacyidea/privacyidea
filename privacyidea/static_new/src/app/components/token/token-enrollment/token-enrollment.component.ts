import {
  Component,
  computed,
  effect,
  HostListener,
  Injectable,
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
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
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
  BasicEnrollmentOptions,
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
import { Observable } from 'rxjs';

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

  // Signals for basic enrollment options, to be replaced by FormControls
  tokenTypeOptions = this.tokenService.tokenTypeOptions;
  selectedTokenType = this.tokenService.selectedTokenType; // This will become a FormControl

  pollResponse: WritableSignal<any> = linkedSignal({
    source: this.selectedTokenType,
    computation: () => null,
  });

  enrollResponse: WritableSignal<EnrollmentResponse | null> = signal(null);
  // Effect to reset enrollResponse when token type changes, if selectedTokenTypeControl is used as source
  // Alternatively, keep linkedSignal if selectedTokenType (service signal) is the desired source.
  // For simplicity and consistency with formGroup driving state:

  // FormControls for the main enrollment form
  selectedTokenTypeControl = new FormControl(
    this.tokenService.selectedTokenType(),
    [Validators.required],
  );
  descriptionControl = new FormControl<string>('', { nonNullable: true });
  selectedUserRealmControl = new FormControl(
    this.userService.selectedUserRealm(),
    [Validators.required],
  );
  userNameFilterControl = new FormControl(this.userService.userNameFilter(), [
    Validators.required,
  ]);
  setPinControl = new FormControl<string>('', this.pinValidator.bind(this));
  repeatPinControl = new FormControl<string>('', this.pinValidator.bind(this));

  pinValidator(): { [key: string]: boolean } | null {
    return this.formGroup.get('setPin')?.value !==
      this.formGroup.get('repeatPin')?.value
      ? { pinMismatch: true }
      : null;
  }

  selectedContainerControl = new FormControl(
    this.containerService.selectedContainer(),
  );

  selectedStartDateControl = new FormControl<Date | null>(new Date());
  selectedStartTimeControl = new FormControl<string>('00:00');
  selectedTimezoneOffsetControl = new FormControl<string>('+00:00');
  selectedEndDateControl = new FormControl<Date | null>(new Date());
  selectedEndTimeControl = new FormControl<string>('23:59');

  onlyAddToRealm = computed(() => {
    if (this.selectedTokenTypeControl.value?.key === '4eyes') {
      const foureyesControls = this.additionalFormFields();
      const control = foureyesControls[
        'onlyAddToRealm'
      ] as FormControl<boolean>; // Key from EnrollFoureyesComponent
      return !!control?.value;
    }
    return false;
  });

  clickEnroll?: (
    enrollementOptions: BasicEnrollmentOptions,
  ) => Observable<EnrollmentResponse> | undefined;
  updateClickEnroll(
    event: (
      enrollementOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined,
  ): void {
    this.clickEnroll = event;
  }

  // This signal might not be needed if children manage their forms entirely.
  additionalFormFields: WritableSignal<{
    [key: string]: FormControl<any>;
  }> = signal({});
  updateAdditionalFormFields(event: {
    [key: string]: FormControl<any> | undefined | null; // Allow undefined/null temporarily for safety
  }): void {
    // Filter out any null or undefined controls before setting the signal
    const validControls: { [key: string]: FormControl<any> } = {};
    for (const key in event) {
      if (event.hasOwnProperty(key) && event[key] instanceof FormControl) {
        validControls[key] = event[key];
      } else {
        console.warn(
          `Ignoring invalid form control for key "${key}" emitted by child component.`,
        );
      }
    }
    this.additionalFormFields.set(validControls);
  }

  formGroup = new FormGroup({
    selectedTokenType: this.selectedTokenTypeControl,
    description: this.descriptionControl,
    selectedUserRealm: this.selectedUserRealmControl,
    userNameFilter: this.userNameFilterControl,
    setPin: this.setPinControl,
    repeatPin: this.repeatPinControl,
    selectedContainer: this.selectedContainerControl,
    selectedStartDate: this.selectedStartDateControl,
    selectedStartTime: this.selectedStartTimeControl,
    selectedTimezoneOffset: this.selectedTimezoneOffsetControl,
    selectedEndDate: this.selectedEndDateControl,
    selectedEndTime: this.selectedEndTimeControl,
  });

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
  ) {
    effect(() => {
      const tokenType = this.selectedTokenTypeControl.value;
      if (tokenType) {
        // Reset enrollResponse when token type changes
        // This replaces the linkedSignal behavior if its source was this.selectedTokenTypeControl
        if (this.enrollResponse() !== null) {
          this.enrollResponse.set(null);
        }
        this.descriptionControl.setValue('');
        this.setPinControl.setValue('');
        this.repeatPinControl.setValue('');
        // Reset other relevant controls if needed when token type changes
        // Reset additional form fields when token type changes
        this.additionalFormFields.set({});
      }
    });

    // Sync signal with FormControl for selectedTokenType
    this.selectedTokenTypeControl.valueChanges.subscribe((value) => {
      if (value) {
        this.tokenService.selectedTokenType.set(value);
      }
    });
    // Sync FormControls with service states for user/realm/container
    this.selectedUserRealmControl.valueChanges.subscribe((value) =>
      this.userService.selectedUserRealm.set(value ?? ''),
    );
    this.userNameFilterControl.valueChanges.subscribe((value) =>
      this.userService.userNameFilter.set(value ?? ''),
    );
    this.selectedContainerControl.valueChanges.subscribe((value) =>
      this.containerService.selectedContainer.set(value ?? ''),
    );
  }

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
    if (this.formGroup.invalid) {
      this.notificationService.openSnackBar(
        'Please fill in all required fields.',
      );
      this.formGroup.markAllAsTouched();
      return;
    }
    if (this.clickEnroll !== undefined) {
      const basicOptions: BasicEnrollmentOptions = {
        type: this.selectedTokenTypeControl.value!.key, // Already validated by formGroup
        description: this.descriptionControl.value.trim(),
        container_serial: this.selectedContainerControl.value?.trim() ?? '',
        validity_period_start: this.formatDateTimeOffset(
          this.selectedStartDateControl.value ?? new Date(),
          this.selectedStartTimeControl.value ?? '00:00',
          this.selectedTimezoneOffsetControl.value ?? '+00:00',
        ),
        validity_period_end: this.formatDateTimeOffset(
          this.selectedEndDateControl.value ?? new Date(),
          this.selectedEndTimeControl.value ?? '23:59',
          this.selectedTimezoneOffsetControl.value ?? '+00:00',
        ),
        user: this.userNameFilterControl.value!.trim(), // Already validated
        pin: this.setPinControl.value ?? '',
      };

      const enrollObservable = this.clickEnroll(basicOptions);
      if (!enrollObservable) {
        this.notificationService.openSnackBar(
          'Failed to enroll token. No response returned.',
        );
        console.error('Failed to enroll token. No response returned.');
        return;
      }
      enrollObservable.subscribe({
        next: (enrollmentResponse) => {
          this.enrollResponse.set(enrollmentResponse);
          this.handleEnrollmentResponse(enrollmentResponse);
        },
        error: (error) => {
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to enroll token. ' + message,
          );
        },
      });
    } else {
      this.notificationService.openSnackBar(
        'Enrollment action is not available for the selected token type.',
      );
    }
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
      this.selectedTokenTypeControl.value?.key ?? '',
    );
  }

  protected openSecondStepDialog(response: EnrollmentResponse | null) {
    if (!response) {
      this.notificationService.openSnackBar(
        'No enrollment response available.',
      );
      return;
    }
    this.secondDialog.open(TokenEnrollmentSecondStepDialogComponent, {
      data: {
        response: response,
        enrollToken: this.enrollToken.bind(this),
        username: this.userService.userNameFilter(),
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

    switch (this.selectedTokenTypeControl.value?.key) {
      case 'webauthn':
      case 'passkey':
      case 'push':
        // The multi-step logic for webauthn, passkey, push is now
        // encapsulated within their respective onClickEnroll methods.
        // The parent component just needs to know when to poll.
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
