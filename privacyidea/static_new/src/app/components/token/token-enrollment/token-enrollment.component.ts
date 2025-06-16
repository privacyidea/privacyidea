import {
  Component,
  computed,
  effect,
  HostListener,
  Injectable,
  linkedSignal,
  signal,
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
  ValidationErrors,
  AbstractControl,
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
  EnrollmentResponse,
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
import { TokenEnrollmentData } from '../../../mappers/token-api-payload/_token-api-payload.mapper';

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
  descriptionControl = new FormControl<string>('', { nonNullable: true });
  selectedUserRealmControl = new FormControl(
    this.userService.selectedUserRealm(),
  );
  userNameFilterControl = new FormControl(this.userService.userNameFilter());
  setPinControl = new FormControl<string>('');
  repeatPinControl = new FormControl<string>('');

  static pinMismatchValidator(
    group: AbstractControl,
  ): { [key: string]: boolean } | null {
    const setPin = group.get('setPin');
    const repeatPin = group.get('repeatPin');
    return setPin && repeatPin && setPin.value !== repeatPin.value
      ? { pinMismatch: true }
      : null;
  }

  selectedContainerControl = new FormControl(
    this.containerService.selectedContainer(),
  );

  selectedStartDateControl = new FormControl<Date | null>(null);
  selectedStartTimeControl = new FormControl<string>('00:00');
  selectedTimezoneOffsetControl = new FormControl<string>('+00:00');
  selectedEndDateControl = new FormControl<Date | null>(null);
  selectedEndTimeControl = new FormControl<string>('23:59');

  onlyAddToRealm = computed(() => {
    if (this.tokenService.selectedTokenType()?.key === '4eyes') {
      const foureyesControls = this.additionalFormFields();
      const control = foureyesControls[
        'onlyAddToRealm'
      ] as FormControl<boolean>; // Key from EnrollFoureyesComponent
      return !!control?.value;
    }
    return false;
  });

  clickEnroll?: (
    enrollementOptions: TokenEnrollmentData,
  ) => Observable<EnrollmentResponse> | undefined;
  updateClickEnroll(
    event: (
      enrollementOptions: TokenEnrollmentData,
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
    this.formGroup = new FormGroup(
      {
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
        ...validControls, // Spread valid controls into the formGroup
      },
      { validators: TokenEnrollmentComponent.pinMismatchValidator },
    );
  }

  formGroup = new FormGroup(
    {
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
    },
    { validators: TokenEnrollmentComponent.pinMismatchValidator },
  );

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
    // The effect will call resetForm on initialization and on subsequent changes to selectedTokenType
    effect(() => {
      this.tokenService.selectedTokenType(); // Establish dependency on the signal
      this.resetForm();
    });
  }

  ngOnInit(): void {
    // Sync FormControls with service states for user/realm/container
    this.selectedUserRealmControl.valueChanges.subscribe((value) => {
      this.userService.userNameFilter.set(''); // Reset userNameFilter when realm changes
      if (!value) {
        this.userNameFilterControl.disable({ emitEvent: false });
      } else {
        this.userNameFilterControl.enable({ emitEvent: false });
      }
      return this.userService.selectedUserRealm.set(value ?? '');
    });
    this.userNameFilterControl.valueChanges.subscribe((value) =>
      this.userService.userNameFilter.set(value ?? ''),
    );
    this.selectedContainerControl.valueChanges.subscribe((value) =>
      this.containerService.selectedContainer.set(value ?? ''),
    );
  }

  resetForm(): void {
    this.userService.selectedUserRealm.set('');
    this.userService.userNameFilter.set('');

    this.formGroup.reset({
      description: '',
      selectedUserRealm: '',
      userNameFilter: '',
      setPin: '',
      repeatPin: '',
      selectedContainer: this.containerService.selectedContainer(),
      selectedStartDate: new Date(),
      selectedStartTime: '00:00',
      selectedTimezoneOffset: '+00:00',
      selectedEndDate: new Date(),
      selectedEndTime: '23:59',
    });
    this.enrollResponse.set(null);
    this.pollResponse.set(null);
    this.additionalFormFields.set({});
    this.formGroup.markAsPristine();
    this.formGroup.markAsUntouched();
    // Reset the pollResponse signal
    this.pollResponse.set(null);
    // Reset the enrollResponse signal
    this.enrollResponse.set(null);

    const isUserRequiredByTokenType = this.userIsRequired();
    // _userInOptionsValidator is now checked only on enrollToken()
    this.selectedUserRealmControl.setValidators(
      isUserRequiredByTokenType ? [Validators.required] : [],
    );
    this.selectedUserRealmControl.updateValueAndValidity({ emitEvent: false });
    this.userNameFilterControl.setValidators(
      isUserRequiredByTokenType ? [Validators.required] : [],
    );
    this.userNameFilterControl.updateValueAndValidity({ emitEvent: false });
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
    const currentTokenType = this.tokenService.selectedTokenType();
    var everythingIsValid = true;
    if (!currentTokenType) {
      this.notificationService.openSnackBar('Please select a token type.');
      return;
    }

    if (!this.validateUserNameFilterControl()) {
      everythingIsValid = false;
    }

    // Validate username against options if a username is entered
    const userNameValue = this.userNameFilterControl.value?.trim();
    if (
      userNameValue &&
      !this.userService.userOptions().includes(userNameValue) &&
      !everythingIsValid
    ) {
      everythingIsValid = false;
      if (!this.userNameFilterControl.hasError('userNotInOptions')) {
        this.userNameFilterControl.setErrors({ userNotInOptions: true });
      }
    } else if (this.userNameFilterControl.hasError('userNotInOptions')) {
      const currentErrors = { ...this.userNameFilterControl.errors };
      delete currentErrors['userNotInOptions'];
      this.userNameFilterControl.setErrors(
        Object.keys(currentErrors).length > 0 ? currentErrors : null,
      );
    }

    if (this.formGroup.invalid) {
      this.notificationService.openSnackBar(
        'Please fill in all required fields or correct invalid entries.',
      );
      this.formGroup.markAllAsTouched();
      return;
    }
    if (this.clickEnroll) {
      const basicOptions: TokenEnrollmentData = {
        type: currentTokenType.key,
        description: this.descriptionControl.value.trim(),
        containerSerial: this.selectedContainerControl.value?.trim() ?? '',
        validityPeriodStart: this.formatDateTimeOffset(
          this.selectedStartDateControl.value ?? new Date(),
          this.selectedStartTimeControl.value ?? '00:00',
          this.selectedTimezoneOffsetControl.value ?? '+00:00',
        ),
        validityPeriodEnd: this.formatDateTimeOffset(
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

  validateUserNameFilterControl(): boolean {
    // Validate username against options if a username is entered
    const userNameValue = this.userNameFilterControl.value;
    if (
      userNameValue &&
      !this.userService.userOptions().includes(userNameValue)
    ) {
      // Validation failed, set 'userNotInOptions' error when needed
      if (!this.userNameFilterControl.hasError('userNotInOptions')) {
        this.userNameFilterControl.setErrors({ userNotInOptions: true });
      }
      return false; // Indicate that validation failed
    }
    // Validation passed, clear any existing 'userNotInOptions' error
    if (this.userNameFilterControl.hasError('userNotInOptions')) {
      const currentErrors = { ...this.userNameFilterControl.errors };
      delete currentErrors['userNotInOptions'];
      this.userNameFilterControl.setErrors(
        Object.keys(currentErrors).length > 0 ? currentErrors : null,
      );
    }
    return true; // Indicate that validation passed
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
      this.tokenService.selectedTokenType()?.key ?? '',
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

    switch (this.tokenService.selectedTokenType()?.key) {
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
