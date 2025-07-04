import {
  AfterViewInit,
  Component,
  computed,
  effect,
  ElementRef,
  Injectable,
  linkedSignal,
  OnDestroy,
  Renderer2,
  signal,
  WritableSignal,
  ViewChild,
  untracked,
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
  AbstractControl,
  ReactiveFormsModule,
  Validators,
  ValidatorFn,
  ValidationErrors,
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
import { UserData, UserService } from '../../../services/user/user.service';
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
import { ContentService } from '../../../services/content/content.service';

import { lastValueFrom, Observable } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../mappers/token-api-payload/_token-api-payload.mapper';
import { DialogService } from '../../../services/dialog/dialog.service';
import { TokenEnrollmentLastStepDialogData } from './token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component';
import {
  MatTooltipModule,
  MAT_TOOLTIP_DEFAULT_OPTIONS,
  MatTooltipDefaultOptions,
} from '@angular/material/tooltip';

export type ClickEnrollFn = (
  enrollementOptions: TokenEnrollmentData,
) => Promise<EnrollmentResponse | null> | Observable<EnrollmentResponse | null>;

export type ReopenDialogFn =
  | (() =>
      | Promise<EnrollmentResponse | null>
      | Observable<EnrollmentResponse | null>)
  | undefined;

export const CUSTOM_TOOLTIP_OPTIONS: MatTooltipDefaultOptions = {
  showDelay: 500,
  touchLongPressShowDelay: 500,
  hideDelay: 0,
  touchendHideDelay: 0,
  disableTooltipInteractivity: true,
};

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
    MatTooltipModule,
  ],
  providers: [
    provideNativeDateAdapter(),
    { provide: DateAdapter, useFactory: () => new CustomDateAdapter('+00:00') },
    { provide: MAT_DATE_FORMATS, useValue: CUSTOM_DATE_FORMATS },
    { provide: MAT_TOOLTIP_DEFAULT_OPTIONS, useValue: CUSTOM_TOOLTIP_OPTIONS },
  ],
  templateUrl: './token-enrollment.component.html',
  styleUrls: ['./token-enrollment.component.scss'],
  standalone: true,
})
export class TokenEnrollmentComponent implements AfterViewInit, OnDestroy {
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

  enrollResponse: WritableSignal<EnrollmentResponse | null> = linkedSignal({
    source: this.selectedTokenType,
    computation: () => null,
  });

  @ViewChild('scrollContainer') scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild('stickyHeader') stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild('stickySentinel') stickySentinel!: ElementRef<HTMLElement>;

  private observer!: IntersectionObserver;

  // Effect to reset enrollResponse when token type changes, if selectedTokenTypeControl is used as source
  // Alternatively, keep linkedSignal if selectedTokenType (service signal) is the desired source.
  // For simplicity and consistency with formGroup driving state:

  // FormControls for the main enrollment form

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

  clickEnroll?: ClickEnrollFn;
  updateClickEnroll(event: ClickEnrollFn): void {
    this.clickEnroll = event;
  }
  reopenDialogSignal: WritableSignal<ReopenDialogFn> = linkedSignal({
    source: this.selectedTokenType,
    computation: () => undefined,
  });
  updateReopenDialog(event: ReopenDialogFn): void {
    this.reopenDialogSignal.set(event);
  }

  // This signal might not be needed if children manage their forms entirely.
  additionalFormFields: WritableSignal<{
    [key: string]: FormControl<any>;
  }> = signal({});

  formGroupSignal: WritableSignal<FormGroup> = linkedSignal({
    source: () => ({
      additionalFormFields: this.additionalFormFields(),
      selectedUserRealm: this.userService.selectedUserRealm(),
      selectedContainer: untracked(() =>
        this.containerService.selectedContainer(),
      ),
      selectedUser: this.userService.selectedUser(),
      defaultRealm: this.realmService.defaultRealm(),
    }),
    computation: (source, previous) => {
      const {
        defaultRealm,
        additionalFormFields,
        selectedUserRealm,
        selectedContainer,
        selectedUser,
      } = source;
      const prevSource = previous?.source;
      const prevFormGroup = previous?.value;
      console.log('Previous: ', previous);
      if (
        !prevFormGroup ||
        !prevSource ||
        selectedUserRealm !== prevSource.selectedUserRealm ||
        additionalFormFields !== prevSource.additionalFormFields
      ) {
        console.log('Creating new FormGroup');
        const selectedUserRealmControl = new FormControl(
          selectedUserRealm || defaultRealm,
          this.isUserRequired ? [Validators.required] : [],
        );
        selectedUserRealmControl.valueChanges.subscribe((value) => {
          this.userFilterControlSignal().reset('', { emitEvent: false });
          if (!value) {
            this.userFilterControlSignal().disable({ emitEvent: false });
          } else {
            this.userFilterControlSignal().enable({ emitEvent: false });
          }
          if (value !== this.userService.selectedUserRealm()) {
            this.userService.selectedUserRealm.set(value ?? '');
          }
        });
        console.log('User filter:', selectedUser);
        const userFilterControl = new FormControl<string | UserData | null>(
          selectedUser,
          this.isUserRequired
            ? [Validators.required, this.userExistsValidator]
            : [this.userExistsValidator],
        );
        userFilterControl.valueChanges.subscribe((value) => {
          this.userService.userFilter.set(value ?? '');
        });

        return new FormGroup(
          {
            description: new FormControl<string>('', { nonNullable: true }),
            selectedUserRealm: selectedUserRealmControl,
            userFilter: userFilterControl,
            setPin: new FormControl<string>('', { nonNullable: true }),
            repeatPin: new FormControl<string>('', { nonNullable: true }),
            selectedContainer: new FormControl(selectedContainer, {
              nonNullable: true,
            }),
            selectedStartDate: new FormControl<Date | null>(new Date(), {
              nonNullable: true,
            }),
            selectedStartTime: new FormControl<string>('00:00', {
              nonNullable: true,
            }),
            selectedTimezoneOffset: new FormControl<string>('+00:00', {
              nonNullable: true,
            }),
            selectedEndDate: new FormControl<Date | null>(new Date(), {
              nonNullable: true,
            }),
            selectedEndTime: new FormControl<string>('23:59', {
              nonNullable: true,
            }),
            ...additionalFormFields,
          },
          { validators: TokenEnrollmentComponent.pinMismatchValidator },
        );
      }
      // // if (selectedUserRealm !== prevSource.selectedUserRealm) {
      // //   console.log(
      // //     'Updating selectedUserRealm in existing FormGroup',
      // //     selectedUserRealm,
      // //   );
      // //   prevFormGroup
      // //     .get('selectedUserRealm')
      // //     ?.setValue(selectedUserRealm, { emitEvent: false });
      // // }
      // if (selectedContainer !== prevSource.selectedContainer) {
      //   console.log(
      //     'Updating selectedContainer in existing FormGroup',
      //     selectedContainer,
      //   );
      //   prevFormGroup
      //     .get('selectedContainer')
      //     ?.setValue(selectedContainer, { emitEvent: false });
      // }
      if (selectedUser !== prevFormGroup.value) {
        console.log('Updating userFilter in existing FormGroup', selectedUser);
        prevFormGroup
          .get('userFilter')
          ?.setValue(selectedUser, { emitEvent: false });
      }
      prevFormGroup.updateValueAndValidity({ emitEvent: false });
      return prevFormGroup;
    },
  });

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

  descriptionControlSignal: WritableSignal<FormControl<string>> = linkedSignal({
    source: this.formGroupSignal,
    computation: (formGroup) =>
      formGroup.get('description') as FormControl<string>,
  });
  selectedUserRealmControlSignal: WritableSignal<FormControl<string>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) => {
        const control = formGroup.get(
          'selectedUserRealm',
        ) as FormControl<string>;

        return control;
      },
    });

  userFilterControlSignal: WritableSignal<FormControl> = linkedSignal({
    source: () => this.formGroupSignal(),
    computation: (formGroup) => {
      return formGroup.get('userFilter') as FormControl<
        string | UserData | null
      >;
    },
  });

  setPinControlSignal: WritableSignal<FormControl<string>> = linkedSignal({
    source: this.formGroupSignal,
    computation: (formGroup) => formGroup.get('setPin') as FormControl<string>,
  });
  repeatPinControlSignal: WritableSignal<FormControl<string>> = linkedSignal({
    source: this.formGroupSignal,
    computation: (formGroup) =>
      formGroup.get('repeatPin') as FormControl<string>,
  });
  selectedContainerControlSignal: WritableSignal<FormControl<string>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) => {
        const control = formGroup.get(
          'selectedContainer',
        ) as FormControl<string>;
        control.valueChanges.subscribe((value) =>
          this.containerService.selectedContainer.set(value ?? ''),
        );
        return control;
      },
    });
  selectedStartDateControlSignal: WritableSignal<FormControl<Date | null>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) =>
        formGroup.get('selectedStartDate') as FormControl<Date | null>,
    });
  selectedStartTimeControlSignal: WritableSignal<FormControl<string>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) =>
        formGroup.get('selectedStartTime') as FormControl<string>,
    });
  selectedTimezoneOffsetControlSignal: WritableSignal<FormControl<string>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) =>
        formGroup.get('selectedTimezoneOffset') as FormControl<string>,
    });
  selectedEndDateControlSignal: WritableSignal<FormControl<Date | null>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) =>
        formGroup.get('selectedEndDate') as FormControl<Date | null>,
    });
  selectedEndTimeControlSignal: WritableSignal<FormControl<string>> =
    linkedSignal({
      source: this.formGroupSignal,
      computation: (formGroup) =>
        formGroup.get('selectedEndTime') as FormControl<string>,
    });

  constructor(
    protected containerService: ContainerService,
    protected realmService: RealmService,
    protected notificationService: NotificationService,
    protected userService: UserService,
    protected tokenService: TokenService,
    protected versioningService: VersionService,
    protected contentService: ContentService,
    protected dialogService: DialogService,
    private renderer: Renderer2,
  ) {
    effect(() => {
      const users = this.userService.filteredUsers();
      if (
        users.length === 1 &&
        this.userFilterControlSignal().value === users[0].username
      ) {
        // If there's only one user, set the userFilterControl to that user
        this.userFilterControlSignal().setValue(users[0]);
      }
    });
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

    const options = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1],
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const isSticky = entry.boundingClientRect.top < entry.rootBounds.top;

      if (isSticky) {
        this.renderer.addClass(this.stickyHeader.nativeElement, 'is-sticky');
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, 'is-sticky');
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    if (this.observer) {
      this.observer.disconnect();
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

  protected async enrollToken(): Promise<void> {
    const currentTokenType = this.tokenService.selectedTokenType();
    var everythingIsValid = true;
    if (!currentTokenType) {
      this.notificationService.openSnackBar('Please select a token type.');
      return;
    }

    const user = this.userService.selectedUser();
    if (this.isUserRequired && !user) {
      everythingIsValid = false;
    }

    if (this.formGroupSignal().invalid) {
      this.formGroupSignal().markAllAsTouched();
      everythingIsValid = false;
    }

    if (!everythingIsValid) {
      this.notificationService.openSnackBar(
        'Please fill in all required fields or correct invalid entries.',
      );
      return;
    }

    if (!this.clickEnroll) {
      this.notificationService.openSnackBar(
        'Enrollment action is not available for the selected token type.',
      );
      return;
    }
    const basicOptions: TokenEnrollmentData = {
      type: currentTokenType.key,
      description: this.descriptionControlSignal().value.trim(),
      containerSerial:
        this.selectedContainerControlSignal().value?.trim() ?? '',
      validityPeriodStart: this.formatDateTimeOffset(
        this.selectedStartDateControlSignal().value ?? new Date(),
        this.selectedStartTimeControlSignal().value ?? '00:00',
        this.selectedTimezoneOffsetControlSignal().value ?? '+00:00',
      ),
      validityPeriodEnd: this.formatDateTimeOffset(
        this.selectedEndDateControlSignal().value ?? new Date(),
        this.selectedEndTimeControlSignal().value ?? '23:59',
        this.selectedTimezoneOffsetControlSignal().value ?? '+00:00',
      ),
      user: user?.username ?? '',
      pin: this.setPinControlSignal().value ?? '',
    };

    const enrollResponse = this.clickEnroll(basicOptions);
    var enrollPromise: Promise<EnrollmentResponse | null>;
    if (enrollResponse instanceof Promise) {
      enrollPromise = enrollResponse;
    } else if (enrollResponse instanceof Observable) {
      enrollPromise = lastValueFrom(enrollResponse);
    } else {
      this.notificationService.openSnackBar(
        'Failed to enroll token. No response returned.',
      );
      console.error('Failed to enroll token. No response returned.');
      return;
    }
    enrollPromise.catch((error) => {
      const message = error.error?.result?.error?.message || '';
      this.notificationService.openSnackBar(
        `Failed to enroll token: ${message || error.message || error}`,
      );
    });
    const enrollmentResponse = await enrollPromise;
    this.enrollResponse.set(enrollmentResponse);
    if (enrollmentResponse) {
      this._handleEnrollmentResponse({
        response: enrollmentResponse,
        user: user,
      });
    }
  }

  _lastTokenEnrollmentLastStepDialogData: WritableSignal<TokenEnrollmentLastStepDialogData | null> =
    linkedSignal({
      source: this.tokenService.selectedTokenType,
      computation: () => null,
    });

  canReopenEnrollmentDialog = computed(
    () =>
      !!this.reopenDialogSignal() ||
      !!this._lastTokenEnrollmentLastStepDialogData(),
  );

  reopenEnrollmentDialog() {
    const reopenFunction = this.reopenDialogSignal();
    if (reopenFunction) {
      reopenFunction();
      return;
    }
    const lastStepData = this._lastTokenEnrollmentLastStepDialogData();
    if (lastStepData) {
      this.dialogService.openTokenEnrollmentLastStepDialog({
        data: lastStepData,
      });
      return;
    }
  }

  get isUserRequired() {
    return ['tiqr', 'webauthn', 'passkey', 'certificate'].includes(
      this.tokenService.selectedTokenType()?.key ?? '',
    );
  }

  protected openLastStepDialog(args: {
    response: EnrollmentResponse | null;
    user: UserData | null;
  }): void {
    const { response, user } = args;
    if (!response) {
      this.notificationService.openSnackBar(
        'No enrollment response available.',
      );
      return;
    }

    const dialogData: TokenEnrollmentLastStepDialogData = {
      response: response,
      enrollToken: this.enrollToken.bind(this),
      user: user,
      userRealm: this.userService.selectedUserRealm(),
      onlyAddToRealm: this.onlyAddToRealm(),
    };
    this._lastTokenEnrollmentLastStepDialogData.set(dialogData);
    this.dialogService.openTokenEnrollmentLastStepDialog({
      data: dialogData,
    });
  }

  userExistsValidator: ValidatorFn = (
    control: AbstractControl<string | UserData | null>,
  ): ValidationErrors | null => {
    const value = control.value;
    if (typeof value === 'string' && value !== '') {
      const users = this.userService.users();
      const userFound = users.some((user) => user.username === value);
      return userFound ? null : { userNotInRealm: { value: value } };
    }

    return null;
  };

  static pinMismatchValidator(
    group: AbstractControl,
  ): { [key: string]: boolean } | null {
    const setPin = group.get('setPin');
    const repeatPin = group.get('repeatPin');
    return setPin && repeatPin && setPin.value !== repeatPin.value
      ? { pinMismatch: true }
      : null;
  }

  private _handleEnrollmentResponse(args: {
    response: EnrollmentResponse;
    user: UserData | null;
  }): void {
    const { response, user } = args;
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === 'clientwait') {
      return;
    }

    if (this.isUserRequired && !user) {
      this.notificationService.openSnackBar(
        'User is required for this token type, but no user was provided.',
      );
      return;
    }

    this.notificationService.openSnackBar(
      `Token ${detail.serial} enrolled successfully.`,
    );
    this.openLastStepDialog({ response, user });
  }
}
