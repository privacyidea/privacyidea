/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import {
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  Injectable,
  linkedSignal,
  OnDestroy,
  OnInit,
  signal,
  Type,
  viewChild
} from "@angular/core";
import { FieldTree, form, FormField, validate, ValidationError } from "@angular/forms/signals";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
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
import { MAT_TOOLTIP_DEFAULT_OPTIONS, MatTooltipModule } from "@angular/material/tooltip";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  ContainerCreateDialogComponent,
  ContainerCreateDialogData
} from "@components/container/container-create-dialog/container-create-dialog.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { EnrollmentPinComponent } from "@components/shared/enrollment-pin/enrollment-pin.component";
import { EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import { EnrollmentFlow } from "@components/token/token-enrollment/enrollment-flow";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { UserAssignmentComponent } from "@components/token/user-assignment/user-assignment.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { EnrollTokenArguments, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { ERR, markRequired, mustEqual } from "@utils/form-rules.utils";
import { clearField, hasError, touchAll } from "@utils/form-state.utils";
import { lastValueFrom, Observable } from "rxjs";
import { TokenEnrollmentTypeSelectorComponent } from "./token-enrollment-type-selector/token-enrollment-type-selector.component";
import {
  CUSTOM_TOOLTIP_OPTIONS,
  NO_PIN_TOKEN_TYPES,
  NO_REALM_ONLY_TOKEN_TYPES,
  USER_REQUIRED_TOKEN_TYPES
} from "./token-enrollment.constants";

const DEFAULT_TIMEZONE_OFFSET = "+00:00";
const DEFAULT_START_TIME = "00:00";
const DEFAULT_END_TIME = "23:59";

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
    FormField,
    MatHint,
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
    MatTooltipModule,
    ClearableInputComponent,
    ScrollToTopDirective,
    UserAssignmentComponent,
    EnrollTokenTypeSwitchComponent,
    EnrollmentPinComponent,
    MatError,
    MatIcon,
    TokenEnrollmentTypeSelectorComponent
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
export class TokenEnrollmentComponent implements OnInit, OnDestroy {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly authService: AuthServiceInterface = inject(AuthService);
  timezoneOptions = TIMEZONE_OFFSETS;
  tokenTypeDescription = linkedSignal({
    source: this.tokenService.tokenTypeOptions,
    computation: (tokenTypes) => {
      return tokenTypes.find((type) => type.key === this.tokenService.selectedTokenType().key)?.text;
    }
  });
  serial = signal<string | null>(null);
  readonly userAssignmentComponent = viewChild(UserAssignmentComponent);
  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);

  descriptionRequired = computed(() => {
    const selectedTokenType = this.tokenService.selectedTokenType();
    return this.authService.requireDescription().includes(selectedTokenType.key);
  });

  isUserRequired = computed(() => USER_REQUIRED_TOKEN_TYPES.includes(this.tokenService.selectedTokenType()?.key ?? ""));
  protected readonly showOnlyAddToRealm = computed(
    () => !NO_REALM_ONLY_TOKEN_TYPES.includes(this.tokenService.selectedTokenType()?.key ?? "")
  );
  protected readonly showPinFields = computed(
    () => !NO_PIN_TOKEN_TYPES.includes(this.tokenService.selectedTokenType()?.key ?? "")
  );

  description = signal<string>("");
  setPin = signal<string>("");
  repeatPin = signal<string>("");
  selectedContainer = signal<string>(this.containerService.selectedContainerSerial() ?? "");
  selectedTimezoneOffset = signal<string>(DEFAULT_TIMEZONE_OFFSET);
  selectedStartDate = signal<Date | null>(null);
  selectedStartTime = signal<string>(DEFAULT_START_TIME);
  selectedEndDate = signal<Date | null>(null);
  selectedEndTime = signal<string>(DEFAULT_END_TIME);

  // Bumped by the input reset after an enrollment, so the type-specific inputs are created anew with
  // their defaults.
  protected readonly inputsGeneration = signal(0);
  // Set by each new enrollment and consumed by the first input reset for it. That reset runs when the
  // last step dialog first opens, or when the flow stops before that dialog. A later reopen then keeps
  // the inputs that the user entered for the next token.
  private inputsResetPending = false;
  // False keeps the inputs of the enrolled token, see the wizard.
  protected readonly resetsInputsAfterEnrollment: boolean = true;
  protected readonly lastStepDialogComponent: Type<EnrollmentStep> = TokenEnrollmentLastStepDialogComponent;
  readonly enrollmentFlow = new EnrollmentFlow({
    successStep: () => this.lastStepDialogComponent,
    successBlockedReason: () =>
      this.isUserRequired() && !this.userService.selectedUser()
        ? $localize`:@@token.userRequiredToken:User is required for this token type, but no user was provided.`
        : null,
    onCancelled: () => this.resetEnrollment(),
    onIncomplete: () => this.resetInputsAfterEnrollment(true),
    onCompleted: () => this.resetInputsAfterEnrollment(true)
  });

  protected readonly hasError = hasError;
  protected readonly ERR = ERR;

  descriptionForm = form(this.description, (f) => {
    markRequired(f, () => this.descriptionRequired());
    validate(f, (ctx) => {
      const v = ctx.value();
      const errors: ValidationError[] = [];
      if (this.descriptionRequired() && !v.trim()) errors.push({ kind: ERR.required });
      if (v.length > this.tokenService.maxDescriptionLength) errors.push({ kind: ERR.maxLength });
      return errors;
    });
  });

  setPinForm = form(this.setPin);
  repeatPinForm = form(this.repeatPin, (f) => {
    mustEqual(f, () => this.setPin());
  });
  selectedContainerForm = form(this.selectedContainer);
  selectedTimezoneOffsetForm = form(this.selectedTimezoneOffset);
  selectedStartDateForm = form(this.selectedStartDate);
  selectedStartTimeForm = form(this.selectedStartTime);
  selectedEndDateForm = form(this.selectedEndDate);
  selectedEndTimeForm = form(this.selectedEndTime);

  private readonly allForms: FieldTree<unknown>[] = [
    this.descriptionForm,
    this.setPinForm,
    this.repeatPinForm,
    this.selectedContainerForm,
    this.selectedTimezoneOffsetForm,
    this.selectedStartDateForm,
    this.selectedStartTimeForm,
    this.selectedEndDateForm,
    this.selectedEndTimeForm
  ];

  isDirty = computed(() => this.allForms.some((field) => field().dirty()));

  // Without the assignment component (self-service, wizard) the user comes from the session.
  private readonly userValid = computed(() => {
    const assignment = this.userAssignmentComponent();
    return assignment ? assignment.valid() : !this.isUserRequired() || !!this.userService.selectedUser();
  });

  // A PIN left over from another token type must not block a type whose PIN fields are hidden:
  // the mismatch error has nowhere to show, so the enrollment would fail without a reason.
  enrollmentBlockedReason = computed<string | null>(() => {
    const sw = this.enrollSwitch();
    if (!sw) {
      return null;
    }
    const strategy = sw.currentStrategy();
    if (strategy === undefined && !!this.tokenService.selectedTokenType()?.key) {
      return $localize`:@@token.enrollmentUnsupportedType:Enrollment is not available for this token type.`;
    }
    return strategy?.enrollmentBlockedReason() ?? null;
  });
  isFormInvalid = computed(
    () =>
      !this.descriptionForm().valid() ||
      (this.showPinFields() && !this.repeatPinForm().valid()) ||
      !this.userValid() ||
      !!this.enrollmentBlockedReason()
  );

  canReopenEnrollmentDialog = computed(() => !!this.enrollmentFlow.dialogData());

  protected wizard = false;

  constructor() {
    effect(() => {
      this.containerService.selectedContainerSerial.set(this.selectedContainer());
    });
  }

  ngOnInit(): void {
    this.registerPendingChanges();
  }

  private registerPendingChanges(): void {
    this.pendingChangesService.registerHasChanges(() => this.isDirty());
    this.pendingChangesService.registerValidChanges(
      () => !!this.tokenService.selectedTokenType()?.key && !this.isFormInvalid()
    );
    this.pendingChangesService.registerSave(() => this.enrollToken());
  }

  ngOnDestroy(): void {
    this.containerService.compatibleWithSelectedTokenType.set(null);
    this.pendingChangesService.clearAllRegistrations();
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

  reopenEnrollmentDialog(): void {
    this.enrollmentFlow.resume();
  }

  async enrollToken(): Promise<boolean> {
    const currentTokenType = this.tokenService.selectedTokenType();
    if (!currentTokenType) {
      this.notificationService.warning($localize`:@@token.pleaseSelectToken:Please select a token type.`);
      return false;
    }

    if (this.isFormInvalid()) {
      this.touchFields();
      this.notificationService.warning(
        $localize`:@@token.pleaseFillAll:Please fill in all required fields or correct invalid entries.`
      );
      return false;
    }

    const strategy: EnrollTokenBase | undefined = this.enrollSwitch()?.currentStrategy();
    if (!strategy) {
      this.notificationService.warning(
        $localize`:@@token.enrollmentAction:Enrollment action is not available for the selected token type.`
      );
      return false;
    }

    const user = this.userService.selectedUser();
    let validityPeriodStart = "";
    if (this.selectedStartDate() && this.selectedStartTime()) {
      validityPeriodStart = this.formatDateTimeOffset(
        this.selectedStartDate()!,
        this.selectedStartTime() ?? "00:00",
        this.selectedTimezoneOffset() ?? "+00:00"
      );
    }
    let validityPeriodEnd = "";
    if (this.selectedEndDate() && this.selectedEndTime()) {
      validityPeriodEnd = this.formatDateTimeOffset(
        this.selectedEndDate()!,
        this.selectedEndTime() ?? "23:59",
        this.selectedTimezoneOffset() ?? "+00:00"
      );
    }

    const basicOptions: TokenEnrollmentData = {
      type: currentTokenType.key,
      description: this.description().trim(),
      containerSerial: this.selectedContainer().trim(),
      validityPeriodStart: validityPeriodStart,
      validityPeriodEnd: validityPeriodEnd,
      user: user?.username ?? "",
      realm: this.userService.selectedUserRealm() ?? "",
      onlyAddToRealm: this.userAssignmentComponent()?.onlyAddToRealm() ?? false,
      pin: this.showPinFields() ? (this.setPin() ?? "") : "",
      serial: this.serial()
    };

    const enrollmentArgs: EnrollTokenArguments | null = strategy.buildEnrollmentArgs(basicOptions);
    if (!enrollmentArgs) {
      this.notificationService.warning(
        $localize`:@@token.pleaseFillAll:Please fill in all required fields or correct invalid entries.`
      );
      return false;
    }

    let enrollmentResponse: EnrollmentResponse | null;
    try {
      enrollmentResponse = await this._toPromise(this.tokenService.enrollToken(enrollmentArgs));
    } catch {
      // enrollToken() has already notified about the failure.
      return false;
    }

    this.enrollmentFlow.start(
      {
        response: enrollmentResponse,
        enrollParameters: enrollmentArgs,
        tokenType: enrollmentArgs.data.type,
        username: enrollmentArgs.data.user,
        userRealm: enrollmentArgs.data.realm,
        onlyAddToRealm: enrollmentArgs.data.onlyAddToRealm ?? false,
        rollover: false,
        showEnrollData: strategy.showEnrollDataInLastStep,
        wizard: this.wizard
      },
      enrollmentResponse ? (strategy.firstStep?.(enrollmentResponse, enrollmentArgs.data) ?? null) : null
    );
    this.inputsResetPending = true;
    // The inputs of the enrolled token are not unsaved changes any more. The input reset registers
    // the guard again for the next token.
    this.pendingChangesService.clearAllRegistrations();
    if (!enrollmentResponse) {
      this.resetInputsAfterEnrollment(true);
      return true;
    }
    this.enrollmentFlow.continue(enrollmentResponse);
    return true;
  }

  resetEnrollment(): void {
    this.inputsResetPending = false;
    this.enrollmentFlow.reset();
    // The enrollment was cancelled and its token deleted, so the inputs are unsaved changes again.
    if (!this.destroyRef.destroyed) {
      this.registerPendingChanges();
    }
  }

  protected clearContainer(): void {
    clearField(this.selectedContainerForm, "");
  }

  // Marks every field touched so each required or invalid field shows its error.
  private touchFields(): void {
    for (const field of this.allForms) {
      void touchAll(field);
    }
    const assignment = this.userAssignmentComponent();
    if (assignment) {
      void touchAll(assignment.realmForm);
      void touchAll(assignment.userFilterForm);
    }
  }

  // Clears the inputs of the enrolled token once per enrollment, so the next enrollment starts from
  // the defaults, and registers the guard again for the next token. User, realm and container stay
  // selected, so several tokens can be enrolled for them in a row. With recreateTypeInputs, the
  // type-specific inputs are also created anew.
  private resetInputsAfterEnrollment(recreateTypeInputs: boolean): void {
    // A dialog can close after the user left the page. A guard registered then would outlive it.
    if (!this.inputsResetPending || this.destroyRef.destroyed) {
      return;
    }
    this.inputsResetPending = false;
    if (!this.resetsInputsAfterEnrollment) {
      return;
    }
    this.descriptionForm().reset("");
    this.setPinForm().reset("");
    this.repeatPinForm().reset("");
    this.selectedTimezoneOffsetForm().reset(DEFAULT_TIMEZONE_OFFSET);
    this.selectedStartDateForm().reset(null);
    this.selectedStartTimeForm().reset(DEFAULT_START_TIME);
    this.selectedEndDateForm().reset(null);
    this.selectedEndTimeForm().reset(DEFAULT_END_TIME);
    // The container stays selected, but it belongs to the enrolled token. A dirty container field
    // makes the guard offer "Save and exit", which enrolls a second token.
    this.selectedContainerForm().reset();
    if (recreateTypeInputs) {
      this.inputsGeneration.update((generation) => generation + 1);
    }
    this.registerPendingChanges();
  }

  protected containerCreateDialogData(): ContainerCreateDialogData {
    const username = this.userAssignmentComponent()?.onlyAddToRealm()
      ? ""
      : (this.userService.selectedUser()?.username ?? "");
    return {
      username: username || undefined,
      userRealm: username ? (this.userService.selectedUserRealm() ?? "") : undefined,
      checkUserAssignment: true
    };
  }

  protected openContainerCreateDialog(): void {
    this.dialogService
      .openDialog({
        component: ContainerCreateDialogComponent,
        data: this.containerCreateDialogData()
      })
      .afterClosed()
      .subscribe((serial) => {
        if (serial) {
          this.selectedContainer.set(serial);
          // A value set from code leaves the field pristine, so it is marked dirty for the pending-changes guard.
          this.selectedContainerForm().markAsDirty();
        }
      });
  }

  private _toPromise<T>(observable: Observable<T> | Promise<T>): Promise<T> {
    if (observable instanceof Promise) {
      return observable;
    } else {
      return lastValueFrom(observable);
    }
  }
}
