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
  effect,
  inject,
  Injectable,
  linkedSignal,
  OnDestroy,
  OnInit,
  signal,
  ViewChild,
  viewChild,
  WritableSignal
} from "@angular/core";
import { form, FormField, validate, ValidationError } from "@angular/forms/signals";
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
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MAT_TOOLTIP_DEFAULT_OPTIONS, MatTooltipModule } from "@angular/material/tooltip";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
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
  EnrollTokenArguments,
  TokenEnrollmentDialogData,
  TokenService,
  TokenServiceInterface,
  TokenType
} from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { lastValueFrom, Observable } from "rxjs";
import { TokenEnrollmentTypeSelectorComponent } from "./token-enrollment-type-selector/token-enrollment-type-selector.component";
import { CUSTOM_TOOLTIP_OPTIONS } from "./token-enrollment.constants";

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

  protected readonly authService: AuthServiceInterface = inject(AuthService);
  timezoneOptions = TIMEZONE_OFFSETS;
  enrollResponse = linkedSignal<TokenType, EnrollmentResponse | null>({
    source: this.tokenService.selectedTokenType,
    computation: () => null
  });
  tokenTypeDescription = linkedSignal({
    source: this.tokenService.tokenTypeOptions,
    computation: (tokenTypes) => {
      return tokenTypes.find((type) => type.key === this.tokenService.selectedTokenType().key)?.text;
    }
  });
  serial = signal<string | null>(null);
  @ViewChild(UserAssignmentComponent)
  userAssignmentComponent!: UserAssignmentComponent;
  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);

  enrolledDialogData = signal<TokenEnrollmentDialogData | null>(null);

  descriptionRequired = computed(() => {
    const selectedTokenType = this.tokenService.selectedTokenType();
    return this.authService.requireDescription().includes(selectedTokenType.key);
  });

  isUserRequired = computed(() =>
    ["tiqr", "webauthn", "passkey", "certificate"].includes(this.tokenService.selectedTokenType()?.key ?? "")
  );

  description = signal<string>("");
  setPin = signal<string>("");
  repeatPin = signal<string>("");
  selectedContainer = signal<string>(this.containerService.selectedContainerSerial() ?? "");
  selectedTimezoneOffset = signal<string>("+00:00");
  selectedStartDate = signal<Date | null>(null);
  selectedStartTime = signal<string>("00:00");
  selectedEndDate = signal<Date | null>(null);
  selectedEndTime = signal<string>("23:59");
  isDirty = signal<boolean>(false);

  descriptionForm = form(this.description, (f) => {
    validate(f, (ctx) => {
      const v = ctx.value();
      const errors: ValidationError[] = [];
      if (this.descriptionRequired() && !v.trim()) errors.push({ kind: "required" });
      if (v.length > this.tokenService.maxDescriptionLength) errors.push({ kind: "maxlength" });
      return errors;
    });
  });

  setPinForm = form(this.setPin);
  repeatPinForm = form(this.repeatPin, (f) => {
    validate(f, (ctx) => (ctx.value() !== this.setPin() ? [{ kind: "pinMismatch" }] : []));
  });

  isFormInvalid = computed(() => !this.descriptionForm().valid() || !this.repeatPinForm().valid());

  _lastTokenEnrollmentLastStepDialogData: WritableSignal<TokenEnrollmentLastStepDialogData | null> = linkedSignal({
    source: this.tokenService.selectedTokenType,
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
  }

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(
      () =>
        this.isDirty() || this.descriptionForm().dirty() || this.setPinForm().dirty() || this.repeatPinForm().dirty()
    );
    this.pendingChangesService.registerValidChanges(
      () =>
        !!this.tokenService.selectedTokenType()?.key &&
        !this.isFormInvalid() &&
        (!this.isUserRequired() || !!this.userService.selectedUser())
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
      const enrollmentResponse: EnrollmentResponse | null = await enrollPromise;
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

  async enrollToken(): Promise<boolean> {
    const currentTokenType = this.tokenService.selectedTokenType();
    let everythingIsValid = true;
    if (!currentTokenType) {
      this.notificationService.warning($localize`Please select a token type.`);
      return false;
    }

    const user = this.userService.selectedUser();
    if (this.isUserRequired() && !user) {
      everythingIsValid = false;
    }

    if (this.isFormInvalid()) {
      this.descriptionForm().markAsTouched();
      this.repeatPinForm().markAsTouched();
      everythingIsValid = false;
    }

    if (!everythingIsValid) {
      this.notificationService.warning($localize`Please fill in all required fields or correct invalid entries.`);
      return false;
    }

    const strategy: EnrollTokenBase | undefined = this.enrollSwitch()?.currentStrategy();
    if (!strategy) {
      this.notificationService.warning($localize`Enrollment action is not available for the selected token type.`);
      return false;
    }

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
      onlyAddToRealm: this.userAssignmentComponent?.onlyAddToRealm() ?? false,
      pin: this.setPin() ?? "",
      serial: this.serial()
    };

    const enrollmentArgs: EnrollTokenArguments | null = strategy.buildEnrollmentArgs(basicOptions);
    if (!enrollmentArgs) return false;
    const enrollResponse = this.tokenService.enrollToken(enrollmentArgs);

    const enrollPromise = this._toPromise(enrollResponse);

    enrollPromise.catch((error) => {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to enroll token: ${message || error.message || error}`);
    });
    let enrollmentResponse: EnrollmentResponse | null = await enrollPromise;

    this.enrolledDialogData.set({
      response: enrollmentResponse,
      enrollParameters: enrollmentArgs,
      tokenType: this.tokenService.selectedTokenType().key,
      username: enrollmentArgs.data.user,
      userRealm: enrollmentArgs.data.realm,
      onlyAddToRealm: enrollmentArgs.data.onlyAddToRealm ?? false,
      rollover: false
    });

    // Complete enrollment
    // Push, passkey, webauthn (TODO: maybe we can integrate this into the complete enrollment dialog component)
    if (strategy.onEnrollmentResponse && enrollmentResponse) {
      enrollmentResponse = await strategy.onEnrollmentResponse(enrollmentResponse, enrollmentArgs.data);
    }
    // two step enrollment + handles further enrollment steps (verify + success dialog)
    this.handleCompleteEnrollment(enrollmentResponse);
    this.pendingChangesService.clearAllRegistrations();
    return true;
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
      data: this.enrolledDialogData()
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.enrollResponse.set(result);
        this.enrolledDialogData.set({
          ...this.enrolledDialogData()!,
          showEnrollData: false
        });
        this.handleVerifyEnrollment(result);
      }
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
      data: this.enrolledDialogData()
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.enrollResponse.set(result);
        this._handleEnrollmentResponse(result);
      }
    });
  }

  protected trackChange(): void {
    this.isDirty.set(true);
  }

  protected openLastStepDialog(response: EnrollmentResponse | null): void {
    if (!response) {
      this.notificationService.warning($localize`No enrollment response available.`);
      return;
    }

    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: response
    });

    this.dialogService.openDialog({
      component: TokenEnrollmentLastStepDialogComponent,
      data: this.enrolledDialogData()
    });
  }

  protected _handleEnrollmentResponse(response: EnrollmentResponse): void {
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === "clientwait") {
      return;
    }

    if (this.isUserRequired() && !this.userService.selectedUser() && !this.enrolledDialogData()?.rollover) {
      this.notificationService.warning($localize`User is required for this token type, but no user was provided.`);
      return;
    }

    this.openLastStepDialog(response);
  }

  private _toPromise<T>(observable: Observable<T> | Promise<T>): Promise<T> {
    if (observable instanceof Promise) {
      return observable;
    } else {
      return lastValueFrom(observable);
    }
  }
}
