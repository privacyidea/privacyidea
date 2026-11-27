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
  untracked,
  viewChild,
  WritableSignal
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
import { EnrollmentPolicyErrorComponent } from "@components/shared/enrollment-policy-error/enrollment-policy-error.component";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { EnrollmentPinComponent } from "@components/shared/enrollment-pin/enrollment-pin.component";
import { EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { TokenEnrollmentLastStepDialogData } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { UserAssignmentComponent } from "@components/token/user-assignment/user-assignment.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import {
  EnrollmentPolicies,
  EnrollmentPolicyState,
  EnrollmentPolicyTarget,
  EnrollTokenArguments,
  TokenEnrollmentDialogData,
  TokenService,
  TokenServiceInterface,
  TokenType,
  TokenTypeKey
} from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { toObservable, toSignal } from "@angular/core/rxjs-interop";
import { Debouncer } from "@utils/debounce.utils";
import { ERR, markRequired, mustEqual } from "@utils/form-rules.utils";
import { clearField, hasError, touchAll } from "@utils/form-state.utils";
import { firstValueFrom, lastValueFrom, merge, Observable, of, Subject, switchMap, tap } from "rxjs";
import { EnrollmentPoliciesLoad, enrollmentPolicyState, loadEnrollmentPolicies } from "./enrollment-policy-values";
import { TokenEnrollmentTypeSelectorComponent } from "./token-enrollment-type-selector/token-enrollment-type-selector.component";
import {
  CUSTOM_TOOLTIP_OPTIONS,
  ENROLLMENT_CANCELLED,
  NO_DISMISS_LAST_STEP_TOKEN_TYPES,
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
    EnrollmentPolicyErrorComponent,
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
  /** The token type that is shown, its policies are requested for and that is enrolled. */
  protected readonly tokenType = computed<TokenType>(() => this.tokenService.selectedTokenType());
  enrollResponse = linkedSignal<TokenType, EnrollmentResponse | null>({
    source: () => this.tokenType(),
    computation: () => null
  });
  tokenTypeDescription = linkedSignal({
    source: this.tokenService.tokenTypeOptions,
    computation: (tokenTypes) => {
      return tokenTypes.find((type) => type.key === this.tokenType().key)?.text;
    }
  });
  serial = signal<string | null>(null);
  readonly userAssignmentComponent = viewChild(UserAssignmentComponent);
  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);

  /** The owner the token is enrolled for, read once for the policy request and for the enrollment itself. */
  private readonly enrollmentOwner = computed(() => ({
    user: this.userService.selectedUser()?.username ?? "",
    realm: this.userService.selectedUserRealm() ?? "",
    onlyAddToRealm: this.userAssignmentComponent()?.onlyAddToRealm() ?? false
  }));

  /**
   * The username the policy target is built from. A typed name is applied after the debounce delay, so that
   * not every keystroke requests the policies. A user found in the user list and a cleared user apply at once.
   */
  private readonly policyUsername = signal("");
  private readonly policyUsernameDebouncer = new Debouncer(this.policyUsername);
  private readonly selectedUsername = computed(() => this.userService.selectedUser()?.username ?? "");
  /** True while the typed name is not yet part of the policy target, the policies are then outdated. */
  private readonly policyUsernamePending = computed(() => this.selectedUsername() !== this.policyUsername());
  /** Emits when the typed name was applied, so an Enroll clicked meanwhile can re-check the policy request. */
  private readonly policyUsernameApplied = new Subject<void>();
  private lastRequestedTarget: EnrollmentPolicyTarget | undefined;

  /** The target the enrollment policies are evaluated for, as POST /token/init would see it. */
  readonly enrollmentTarget = computed<EnrollmentPolicyTarget | undefined>(
    () => {
      const type = this.tokenType()?.key;
      if (!type) {
        return undefined;
      }
      const owner = this.enrollmentOwner();
      const user = this.policyUsername();
      const serial = this.serial();
      return {
        type,
        ...(user && !owner.onlyAddToRealm && { user }),
        ...(owner.realm && (user || owner.onlyAddToRealm) && { realm: owner.realm }),
        ...(serial && { serial })
      };
    },
    { equal: (a, b) => JSON.stringify(a) === JSON.stringify(b) }
  );

  private lastLoadedPolicies: EnrollmentPolicies | undefined;
  /** Emits when a policy request ended, so an Enroll clicked while loading can go on with the new policies. */
  private readonly policiesSettled = new Subject<void>();

  /** The enrollment policies of the current target, a new target starts a new request and drops the pending one. */
  private readonly enrollmentPoliciesLoad = toSignal(
    toObservable(this.enrollmentTarget).pipe(
      switchMap((target): Observable<EnrollmentPoliciesLoad> => {
        this.lastRequestedTarget = target;
        if (!target) {
          return of({ status: "idle" });
        }
        return loadEnrollmentPolicies(this.tokenService.getEnrollmentPolicies(target), this.lastLoadedPolicies).pipe(
          tap((load) => {
            if (load.status === "loaded") {
              this.lastLoadedPolicies = load.policies;
            }
            if (load.status !== "loading") {
              this.policiesSettled.next();
            }
          })
        );
      })
    ),
    { initialValue: { status: "idle" } as EnrollmentPoliciesLoad }
  );

  readonly enrollmentPoliciesLoading = computed(
    () => this.enrollmentPoliciesLoad().status === "loading" || this.policyUsernamePending()
  );

  /** The server message when the enrollment policies cannot be determined for the target, else null. */
  readonly enrollmentPoliciesError = computed<string | null>(() => {
    const load = this.enrollmentPoliciesLoad();
    return load.status === "error" ? load.message : null;
  });

  readonly enrollmentPolicyState = computed<EnrollmentPolicyState>(() =>
    enrollmentPolicyState(this.enrollmentPoliciesLoad())
  );

  enrolledDialogData = signal<TokenEnrollmentDialogData | null>(null);

  // While the policies load or fail, Enroll is blocked anyway.
  descriptionRequired = computed(() => {
    const state = this.enrollmentPolicyState();
    return state.state === "loaded" && state.policies.require_description;
  });

  isUserRequired = computed(() => USER_REQUIRED_TOKEN_TYPES.includes(this.tokenType()?.key ?? ""));
  protected readonly showOnlyAddToRealm = computed(
    () => !NO_REALM_ONLY_TOKEN_TYPES.includes(this.tokenType()?.key ?? "")
  );
  protected readonly showPinFields = computed(
    () => !NO_PIN_TOKEN_TYPES.includes(this.tokenType()?.key ?? "")
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
    // Loading alone does not block: enrollToken() waits for the policies instead, so Enroll does not flash disabled.
    const policyError = this.enrollmentPoliciesError();
    if (policyError) {
      return policyError;
    }
    const sw = this.enrollSwitch();
    if (!sw) {
      return null;
    }
    const strategy = sw.currentStrategy();
    if (strategy === undefined && !!this.tokenType()?.key) {
      return $localize`:@@token.enrollmentUnsupportedType:Enrollment is not available for this token type.`;
    }
    return strategy?.enrollmentBlockedReason() ?? null;
  });
  isFormInvalid = computed(
    () =>
      !this.descriptionForm().valid() ||
      (this.showPinFields() && !this.repeatPinForm().valid()) ||
      !this.userValid() ||
      !!this.enrollmentBlockedReason() ||
      !!this.enrollSwitch()?.currentStrategy()?.fieldsInvalid()
  );

  _lastTokenEnrollmentLastStepDialogData: WritableSignal<TokenEnrollmentLastStepDialogData | null> = linkedSignal({
    source: () => this.tokenType(),
    computation: () => null
  });
  canReopenEnrollmentDialog = computed(
    () => !!this.enrollSwitch()?.currentStrategy()?.reopenDialog() || !!this.enrolledDialogData()
  );

  protected wizard = false;

  constructor() {
    effect(() => {
      this.containerService.selectedContainerSerial.set(this.selectedContainer());
    });
    effect(() => {
      const username = this.selectedUsername();
      untracked(() => {
        if (username === this.policyUsername()) {
          this.policyUsernameDebouncer.cancel();
        } else if (!username || this.userService.users().some((user) => user.username === username)) {
          this.policyUsernameDebouncer.set(username);
        } else {
          this.policyUsernameDebouncer.schedule(username);
        }
      });
    });
    effect(() => {
      if (!this.policyUsernamePending()) {
        this.policyUsernameApplied.next();
      }
    });
  }

  ngOnInit(): void {
    this.registerPendingChanges();
  }

  private registerPendingChanges(): void {
    this.pendingChangesService.registerHasChanges(() => this.isDirty());
    this.pendingChangesService.registerValidChanges(
      () => !!this.tokenType()?.key && !this.isFormInvalid()
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

  async reopenEnrollmentDialog() {
    const reopenFunction = this.enrollSwitch()?.currentStrategy()?.reopenDialog();
    if (reopenFunction) {
      const enrollPromise = this._toPromise(reopenFunction());
      if (!enrollPromise) return;
      const enrollmentResponse = await enrollPromise;
      if (enrollmentResponse === ENROLLMENT_CANCELLED) {
        this.resetEnrollment();
        return;
      }
      this.enrollResponse.set(enrollmentResponse);
      if (enrollmentResponse) {
        this._handleEnrollmentResponse(enrollmentResponse);
      }
      return;
    }
    if (this.enrolledDialogData()) {
      this.handleCompleteEnrollment(this.enrolledDialogData()?.response || null);
    }
  }

  // Enroll is disabled while the form is invalid, so a click on it shows every field error instead of submitting.
  revealFieldErrors(): void {
    if (!this.isFormInvalid()) return;
    this.touchFields();
    this.enrollSwitch()
      ?.currentStrategy()
      ?.markFieldsTouched(this.basicEnrollmentOptions(this.tokenType().key));
  }

  private basicEnrollmentOptions(tokenTypeKey: TokenTypeKey): TokenEnrollmentData {
    const owner = this.enrollmentOwner();
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

    return {
      type: tokenTypeKey,
      description: this.description().trim(),
      containerSerial: this.selectedContainer().trim(),
      validityPeriodStart: validityPeriodStart,
      validityPeriodEnd: validityPeriodEnd,
      user: owner.user,
      realm: owner.realm,
      onlyAddToRealm: owner.onlyAddToRealm,
      pin: this.showPinFields() ? (this.setPin() ?? "") : "",
      serial: this.serial()
    };
  }

  async enrollToken(): Promise<boolean> {
    // Never enroll with the policies of the previous target: wait for the ones of the current target.
    // A typed name that was just applied has its request started after the next change detection.
    let waitedForTypedName = false;
    while (true) {
      waitedForTypedName ||= this.policyUsernamePending();
      const requested = JSON.stringify(this.lastRequestedTarget) === JSON.stringify(this.enrollmentTarget());
      if (!this.enrollmentPoliciesLoading() && (requested || !waitedForTypedName)) {
        break;
      }
      await firstValueFrom(merge(this.policiesSettled, this.policyUsernameApplied));
    }
    const currentTokenType = this.tokenType();
    if (!currentTokenType) {
      this.notificationService.warning($localize`:@@token.pleaseSelectToken:Please select a token type.`);
      return false;
    }

    if (this.isFormInvalid()) {
      this.revealFieldErrors();
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

    const basicOptions = this.basicEnrollmentOptions(currentTokenType.key);

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

    this.enrolledDialogData.set({
      response: enrollmentResponse,
      enrollParameters: enrollmentArgs,
      tokenType: enrollmentArgs.data.type,
      username: enrollmentArgs.data.user,
      userRealm: enrollmentArgs.data.realm,
      onlyAddToRealm: enrollmentArgs.data.onlyAddToRealm ?? false,
      rollover: false,
      showEnrollData: strategy.showEnrollDataInLastStep,
      onEnrollmentResponseChange: (response) => this.updateEnrollmentResponse(response)
    });
    this.inputsResetPending = true;

    // Complete enrollment
    // Push, passkey, webauthn (TODO: maybe we can integrate this into the complete enrollment dialog component)
    if (strategy.onEnrollmentResponse && enrollmentResponse) {
      const stepResult = await strategy.onEnrollmentResponse(enrollmentResponse, enrollmentArgs.data);
      if (stepResult === ENROLLMENT_CANCELLED) {
        this.resetEnrollment();
        return true;
      }
      enrollmentResponse = stepResult;
    }
    // The inputs of the enrolled token are not unsaved changes any more. The input reset registers
    // the guard again for the next token.
    this.pendingChangesService.clearAllRegistrations();
    if (!enrollmentResponse) {
      // The step stopped before the enrollment finished, for example because the user closed the push
      // QR dialog in clientwait. The token exists, and the reopen button finishes its enrollment later.
      this.resetInputsBeforeLastStep();
      return true;
    }
    // two step enrollment + handles further enrollment steps (verify + success dialog)
    this.handleCompleteEnrollment(enrollmentResponse);
    return true;
  }

  updateEnrollmentResponse(response: EnrollmentResponse): void {
    this.enrollResponse.set(response);
    this.enrolledDialogData.update((data) => (data ? { ...data, response: response } : data));
  }

  handleCompleteEnrollment(enrollmentResponse: EnrollmentResponse | null): void {
    if (!this.enrolledDialogData() || !enrollmentResponse) return;

    this.enrollResponse.set(enrollmentResponse);
    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: enrollmentResponse
    });

    if (enrollmentResponse?.detail.rollout_state !== "clientwait") {
      return this.handleVerifyEnrollment(enrollmentResponse);
    }

    const dialogRef = this.dialogService.openDialog({
      component: TokenCompleteEnrollmentComponent,
      data: this.enrolledDialogData(),
      configOverride: { autoFocus: "input", disableClose: true }
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result === ENROLLMENT_CANCELLED) {
        this.resetEnrollment();
        return;
      }
      if (!result) {
        // Closed before the second step. The reopen button opens this dialog again.
        this.resetInputsBeforeLastStep();
        return;
      }
      this.enrollResponse.set(result);
      this.enrolledDialogData.set({
        ...this.enrolledDialogData()!,
        showEnrollData: false
      });
      this.handleVerifyEnrollment(result);
    });
  }

  handleVerifyEnrollment(enrollmentResponse: EnrollmentResponse | null): void {
    if (!this.enrolledDialogData() || !enrollmentResponse) return;

    this.enrollResponse.set(enrollmentResponse);
    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: enrollmentResponse
    });

    if (!enrollmentResponse?.detail?.verify) {
      // No verify required, directly open last step dialog
      return this._handleEnrollmentResponse(enrollmentResponse);
    }

    // Open verify dialog
    const dialogRef = this.dialogService.openDialog({
      component: TokenVerifyEnrollmentComponent,
      data: this.enrolledDialogData(),
      configOverride: { autoFocus: "input", disableClose: true }
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result === ENROLLMENT_CANCELLED) {
        this.resetEnrollment();
        return;
      }
      if (!result) {
        // Closed before the verification. The reopen button opens this dialog again.
        this.resetInputsBeforeLastStep();
        return;
      }
      this.enrollResponse.set(result);
      this._handleEnrollmentResponse(result);
    });
  }

  resetEnrollment(): void {
    this.inputsResetPending = false;
    this.enrollResponse.set(null);
    this.enrolledDialogData.set(null);
    this.enrollSwitch()?.currentStrategy()?.reopenDialog.set(undefined);
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

  // For a flow that stops after the token was created, but before the last step dialog. The
  // type-specific inputs stay while their component holds the reopen action that finishes the
  // enrollment (push, WebAuthn, passkey).
  private resetInputsBeforeLastStep(): void {
    const strategyHoldsReopenAction = !!this.enrollSwitch()?.currentStrategy()?.reopenDialog();
    this.resetInputsAfterEnrollment(!strategyHoldsReopenAction);
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

  protected lastStepDialogIsDismissable(): boolean {
    return !NO_DISMISS_LAST_STEP_TOKEN_TYPES.includes(this.enrolledDialogData()?.tokenType ?? "");
  }

  protected openLastStepDialog(response: EnrollmentResponse | null): void {
    if (!response) {
      this.notificationService.warning($localize`:@@token.noEnrollmentResponse:No enrollment response available.`);
      return;
    }

    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: response
    });

    this.dialogService.openDialog({
      component: TokenEnrollmentLastStepDialogComponent,
      data: this.enrolledDialogData(),
      configOverride: { disableClose: !this.lastStepDialogIsDismissable() }
    });
  }

  protected _handleEnrollmentResponse(response: EnrollmentResponse): void {
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === "clientwait") {
      return;
    }

    if (this.isUserRequired() && !this.userService.selectedUser() && !this.enrolledDialogData()?.rollover) {
      this.notificationService.warning(
        $localize`:@@token.userRequiredToken:User is required for this token type, but no user was provided.`
      );
      return;
    }

    this.openLastStepDialog(response);
    // The enrollment is complete. From now on, the reopen button opens the last step dialog from
    // enrolledDialogData, not the first step of push, WebAuthn or passkey again.
    this.enrollSwitch()?.currentStrategy()?.reopenDialog.set(undefined);
    this.resetInputsAfterEnrollment(true);
  }

  private _toPromise<T>(observable: Observable<T> | Promise<T>): Promise<T> {
    if (observable instanceof Promise) {
      return observable;
    } else {
      return lastValueFrom(observable);
    }
  }
}
