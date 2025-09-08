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
import { NgClass } from "@angular/common";
import {
  AfterViewInit,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  Injectable,
  linkedSignal,
  OnDestroy,
  Renderer2,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators
} from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatButton, MatIconButton } from "@angular/material/button";
import {
  DateAdapter,
  MAT_DATE_FORMATS,
  MatNativeDateModule,
  NativeDateAdapter,
  provideNativeDateAdapter
} from "@angular/material/core";
import { MatDatepickerModule } from "@angular/material/datepicker";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatError, MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
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

import { MatCheckbox } from "@angular/material/checkbox";
import { MAT_TOOLTIP_DEFAULT_OPTIONS, MatTooltipDefaultOptions, MatTooltipModule } from "@angular/material/tooltip";
import { lastValueFrom, Observable } from "rxjs";
import { EnrollmentResponse, TokenEnrollmentData } from "../../../mappers/token-api-payload/_token-api-payload.mapper";
import { QuestionApiPayloadMapper } from "../../../mappers/token-api-payload/question-token-api-payload.mapper";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { TokenEnrollmentLastStepDialogData } from "./token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";

export type ClickEnrollFn = (
  enrollmentOptions: TokenEnrollmentData
) => Promise<EnrollmentResponse | null> | Observable<EnrollmentResponse | null>;

export type ReopenDialogFn =
  | (() => Promise<EnrollmentResponse | null> | Observable<EnrollmentResponse | null>)
  | undefined;

export const CUSTOM_TOOLTIP_OPTIONS: MatTooltipDefaultOptions = {
  showDelay: 500,
  touchLongPressShowDelay: 500,
  hideDelay: 0,
  touchendHideDelay: 0,
  disableTooltipInteractivity: true
};

export const CUSTOM_DATE_FORMATS = {
  parse: { dateInput: "YYYY-MM-DD" },
  display: {
    dateInput: "YYYY-MM-DD",
    monthYearLabel: "MMM YYYY",
    dateA11yLabel: "LL",
    monthYearA11yLabel: "MMMM YYYY"
  }
};

export const TIMEZONE_OFFSETS = (() => {
  const offsets = [];
  for (let i = -12; i <= 14; i++) {
    const sign = i < 0 ? "-" : "+";
    const absOffset = Math.abs(i);
    const hours = String(absOffset).padStart(2, "0");
    const label = `UTC${sign}${hours}:00`;
    const value = `${sign}${hours}:00`;
    offsets.push({ label, value });
  }
  return offsets;
})();

@Injectable()
export class CustomDateAdapter extends NativeDateAdapter {
  private timezoneOffset = "+00:00";

  override format(date: Date): string {
    const adjustedDate = this._applyTimezoneOffset(date);
    const year = adjustedDate.getFullYear();
    const month = (adjustedDate.getMonth() + 1).toString().padStart(2, "0");
    const day = adjustedDate.getDate().toString().padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  private _applyTimezoneOffset(date: Date): Date {
    const offsetParts = this.timezoneOffset.split(":").map(Number);
    const offsetMinutes = offsetParts[0] * 60 + (offsetParts[1] || 0);
    const adjustedTime = date.getTime() + offsetMinutes * 60 * 1000;
    return new Date(adjustedTime);
  }
}

@Component({
  selector: "app-token-enrollment",
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
    MatCheckbox,
    ClearableInputComponent,
    ScrollToTopDirective
  ],
  providers: [
    provideNativeDateAdapter(),
    { provide: DateAdapter, useFactory: () => new CustomDateAdapter("+00:00") },
    { provide: MAT_DATE_FORMATS, useValue: CUSTOM_DATE_FORMATS },
    { provide: MAT_TOOLTIP_DEFAULT_OPTIONS, useValue: CUSTOM_TOOLTIP_OPTIONS }
  ],
  templateUrl: "./token-enrollment.component.html",
  styleUrls: ["./token-enrollment.component.scss"],
  standalone: true
})
export class TokenEnrollmentComponent implements AfterViewInit, OnDestroy {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  protected readonly renderer: Renderer2 = inject(Renderer2);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private observer!: IntersectionObserver;
  timezoneOptions = TIMEZONE_OFFSETS;

  enrollResponse: WritableSignal<EnrollmentResponse | null> = linkedSignal({
    source: this.tokenService.selectedTokenType,
    computation: () => null
  });
  tokenTypeDescription: WritableSignal<any> = linkedSignal({
    source: this.tokenService.tokenTypeOptions,
    computation: (tokenTypes) => {
      return tokenTypes.find((type) => type.key === this.tokenService.selectedTokenType().key)?.text;
    }
  });
  serial = signal<string | null>(null);
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  clickEnroll?: ClickEnrollFn;
  reopenDialogSignal: WritableSignal<ReopenDialogFn> = linkedSignal({
    source: this.tokenService.selectedTokenType,
    computation: () => undefined
  });
  additionalFormFields: WritableSignal<{
    [key: string]: FormControl<any>;
  }> = signal({});
  descriptionControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.maxLength(80)]
  });
  selectedUserRealmControl = new FormControl<string>(this.userService.selectedUserRealm(), {
    nonNullable: true
  });
  userFilterControl = new FormControl<string | UserData | null>(this.userService.selectionFilter(), {
    nonNullable: true
  });
  onlyAddToRealmControl = new FormControl<boolean>(false, { nonNullable: true });
  setPinControl = new FormControl<string>("", { nonNullable: true });
  repeatPinControl = new FormControl<string>("", { nonNullable: true });
  selectedContainerControl = new FormControl(this.containerService.selectedContainer(), { nonNullable: true });
  selectedTimezoneOffsetControl = new FormControl<string>("+00:00", {
    nonNullable: true
  });
  selectedStartDateControl = new FormControl<Date | null>(new Date(), {
    nonNullable: true
  });
  selectedStartTimeControl = new FormControl<string>("00:00", {
    nonNullable: true
  });
  selectedEndDateControl = new FormControl<Date | null>(new Date(), {
    nonNullable: true
  });
  selectedEndTimeControl = new FormControl<string>("23:59", {
    nonNullable: true
  });
  _lastTokenEnrollmentLastStepDialogData: WritableSignal<TokenEnrollmentLastStepDialogData | null> = linkedSignal({
    source: this.tokenService.selectedTokenType,
    computation: () => null
  });
  canReopenEnrollmentDialog = computed(
    () => !!this.reopenDialogSignal() || !!this._lastTokenEnrollmentLastStepDialogData()
  );

  constructor() {
    effect(() => {
      const users = this.userService.selectionFilteredUsers();
      if (users.length === 1 && this.userFilterControl.value === users[0].username) {
        this.userFilterControl.setValue(users[0]);
      }
    });
  }

  get isUserRequired() {
    return ["tiqr", "webauthn", "passkey", "certificate"].includes(this.tokenService.selectedTokenType()?.key ?? "");
  }

  static pinMismatchValidator(group: AbstractControl): { [key: string]: boolean } | null {
    const setPin = group.get("setPin");
    const repeatPin = group.get("repeatPin");
    return setPin && repeatPin && setPin.value !== repeatPin.value ? { pinMismatch: true } : null;
  }

  updateClickEnroll(event: ClickEnrollFn): void {
    this.clickEnroll = event;
  }

  updateReopenDialog(event: ReopenDialogFn): void {
    this.reopenDialogSignal.set(event);
  }

  updateAdditionalFormFields(event: { [key: string]: FormControl<any> | undefined | null }): void {
    const validControls: { [key: string]: FormControl<any> } = {};
    for (const key in event) {
      if (event.hasOwnProperty(key) && event[key] instanceof FormControl) {
        validControls[key] = event[key];
      } else {
        console.warn(`Ignoring invalid form control for key "${key}" emitted by child component.`);
      }
    }
    this.additionalFormFields.set(validControls);
  }

  ngOnInit(): void {
    this.selectedContainerControl.valueChanges.subscribe((value) =>
      this.containerService.selectedContainer.set(value ?? "")
    );
    this.userFilterControl.valueChanges.subscribe((value) => {
      this.userService.selectionFilter.set(value ?? "");
      if (value) {
        this.onlyAddToRealmControl.setValue(false, {});
        this.onlyAddToRealmControl.disable({ emitEvent: false });
      } else {
        this.onlyAddToRealmControl.enable({ emitEvent: false });
      }
    });
    this.selectedUserRealmControl.valueChanges.subscribe((value) => {
      this.userFilterControl.reset("", { emitEvent: false });
      if (!value) {
        this.userFilterControl.disable({ emitEvent: false });
      } else {
        this.userFilterControl.enable({ emitEvent: false });
      }

      if (value !== this.userService.selectedUserRealm()) {
        this.userService.selectedUserRealm.set(value ?? "");
      }
    });
    this.onlyAddToRealmControl.valueChanges.subscribe((value) => {
      if (value) {
        this.userFilterControl.disable({ emitEvent: false });
      } else {
        this.userFilterControl.enable({ emitEvent: false });
      }
    });
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

    const options = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const isSticky = entry.boundingClientRect.top < entry.rootBounds.top;

      if (isSticky) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
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
      return "";
    }
    const hours = parseInt(timeMatch[1], 10);
    const minutes = parseInt(timeMatch[2], 10);
    const newDate = new Date(date.getTime());

    newDate.setHours(hours, minutes, 0, 0);

    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, "0");
    const day = String(newDate.getDate()).padStart(2, "0");
    const formattedHours = String(newDate.getHours()).padStart(2, "0");
    const formattedMinutes = String(newDate.getMinutes()).padStart(2, "0");
    const offsetNoColon = offset.replace(":", "");

    return `${year}-${month}-${day}T${formattedHours}:${formattedMinutes}${offsetNoColon}`;
  }

  reopenEnrollmentDialog() {
    const reopenFunction = this.reopenDialogSignal();
    if (reopenFunction) {
      reopenFunction();
      return;
    }
    const lastStepData = this._lastTokenEnrollmentLastStepDialogData();
    if (lastStepData) {
      this.dialogService.openTokenEnrollmentLastStepDialog({
        data: lastStepData
      });
      return;
    }
  }

  userExistsValidator: ValidatorFn = (control: AbstractControl<string | UserData | null>): ValidationErrors | null => {
    const value = control.value;
    if (typeof value === "string" && value !== "") {
      const users = this.userService.users();
      const userFound = users.some((user) => user.username === value);
      return userFound ? null : { userNotInRealm: { value: value } };
    }

    return null;
  };

  formGroupSignal: WritableSignal<FormGroup> = linkedSignal({
    source: () => ({
      additionalFormFields: this.additionalFormFields(),
      selectedUser: this.userService.selectedUser()
    }),
    computation: (source, _previous) => {
      const { additionalFormFields } = source;

      this.selectedUserRealmControl.setValidators(this.isUserRequired ? [Validators.required] : []);

      this.userFilterControl.setValidators(
        this.isUserRequired ? [Validators.required, this.userExistsValidator] : [this.userExistsValidator]
      );

      return new FormGroup(
        {
          description: this.descriptionControl,
          selectedUserRealm: this.selectedUserRealmControl,
          userFilter: this.userFilterControl,
          onlyAddToRealm: this.onlyAddToRealmControl,
          setPin: this.setPinControl,
          repeatPin: this.repeatPinControl,
          selectedContainer: this.selectedContainerControl,
          selectedStartDate: this.selectedStartDateControl,
          selectedStartTime: this.selectedStartTimeControl,
          selectedTimezoneOffset: this.selectedTimezoneOffsetControl,
          selectedEndDate: this.selectedEndDateControl,
          selectedEndTime: this.selectedEndTimeControl,
          ...additionalFormFields
        },
        { validators: TokenEnrollmentComponent.pinMismatchValidator }
      );
    }
  });

  protected async enrollToken(): Promise<void> {
    const currentTokenType = this.tokenService.selectedTokenType();
    let everythingIsValid = true;
    if (!currentTokenType) {
      this.notificationService.openSnackBar("Please select a token type.");
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
      this.notificationService.openSnackBar("Please fill in all required fields or correct invalid entries.");
      return;
    }

    if (!this.clickEnroll) {
      this.notificationService.openSnackBar("Enrollment action is not available for the selected token type.");
      return;
    }

    let validityPeriodStart = "";
    if (this.selectedStartDateControl.value) {
      validityPeriodStart = this.formatDateTimeOffset(
        this.selectedStartDateControl.value,
        this.selectedStartTimeControl.value ?? "00:00",
        this.selectedTimezoneOffsetControl.value ?? "+00:00"
      );
    }
    let validityPeriodEnd = "";
    if (this.selectedEndDateControl.value) {
      validityPeriodEnd = this.formatDateTimeOffset(
        this.selectedEndDateControl.value,
        this.selectedEndTimeControl.value ?? "23:59",
        this.selectedTimezoneOffsetControl.value ?? "+00:00"
      );
    }

    const basicOptions: TokenEnrollmentData = {
      type: currentTokenType.key,
      description: this.descriptionControl.value.trim(),
      containerSerial: this.selectedContainerControl.value?.trim() ?? "",
      validityPeriodStart: validityPeriodStart,
      validityPeriodEnd: validityPeriodEnd,
      user: user?.username ?? "",
      realm: this.selectedUserRealmControl.value ?? "",
      onlyAddToRealm: this.onlyAddToRealmControl.value ?? false,
      pin: this.setPinControl.value ?? "",
      serial: this.serial()
    };

    const enrollResponse = this.clickEnroll(basicOptions);
    let enrollPromise: Promise<EnrollmentResponse | null>;
    if (enrollResponse instanceof Promise) {
      enrollPromise = enrollResponse;
    } else {
      enrollPromise = lastValueFrom(enrollResponse);
    }
    enrollPromise.catch((error) => {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.openSnackBar(`Failed to enroll token: ${message || error.message || error}`);
    });
    const enrollmentResponse = await enrollPromise;
    this.enrollResponse.set(enrollmentResponse);
    if (enrollmentResponse) {
      this._handleEnrollmentResponse({
        response: enrollmentResponse,
        user: user
      });
    }
  }

  protected openLastStepDialog(args: { response: EnrollmentResponse | null; user: UserData | null }): void {
    const { response, user } = args;
    if (!response) {
      this.notificationService.openSnackBar("No enrollment response available.");
      return;
    }

    const dialogData: TokenEnrollmentLastStepDialogData = {
      tokentype: this.tokenService.selectedTokenType(),
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

  private _handleEnrollmentResponse(args: { response: EnrollmentResponse; user: UserData | null }): void {
    const { response, user } = args;
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === "clientwait") {
      return;
    }

    if (this.isUserRequired && !user) {
      this.notificationService.openSnackBar("User is required for this token type, but no user was provided.");
      return;
    }

    this.openLastStepDialog({ response, user });
  }
}
