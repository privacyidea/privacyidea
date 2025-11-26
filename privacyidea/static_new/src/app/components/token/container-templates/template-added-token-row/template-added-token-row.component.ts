import { Component, computed, effect, EventEmitter, input, Output, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { FormControl, FormsModule } from "@angular/forms";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { EnrollHotpComponent } from "../../token-enrollment/enroll-hotp/enroll-hotp.component";
import { EnrollTotpComponent } from "../../token-enrollment/enroll-totp/enroll-totp.component";
import { EnrollSpassComponent } from "../../token-enrollment/enroll-spass/enroll-spass.component";
import { EnrollRemoteComponent } from "../../token-enrollment/enroll-remote/enroll-remote.component";
import { EnrollSmsComponent } from "../../token-enrollment/enroll-sms/enroll-sms.component";
import { EnrollFoureyesComponent } from "../../token-enrollment/enroll-foureyes/enroll-foureyes.component";
import { EnrollApplspecComponent } from "../../token-enrollment/enroll-asp/enroll-applspec.component";
import { EnrollDaypasswordComponent } from "../../token-enrollment/enroll-daypassword/enroll-daypassword.component";
import { EnrollEmailComponent } from "../../token-enrollment/enroll-email/enroll-email.component";
import { EnrollIndexedsecretComponent } from "../../token-enrollment/enroll-indexsecret/enroll-indexedsecret.component";
import { EnrollPaperComponent } from "../../token-enrollment/enroll-paper/enroll-paper.component";
import { EnrollPushComponent } from "../../token-enrollment/enroll-push/enroll-push.component";
import { EnrollRegistrationComponent } from "../../token-enrollment/enroll-registration/enroll-registration.component";
import { EnrollTanComponent } from "../../token-enrollment/enroll-tan/enroll-tan.component";
import { EnrollTiqrComponent } from "../../token-enrollment/enroll-tiqr/enroll-tiqr.component";
import {
  TokenEnrollmentData,
  TokenApiPayloadMapper
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";

@Component({
  selector: "app-template-added-token-row",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatExpansionModule,
    FormsModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    EnrollHotpComponent,
    EnrollTotpComponent,
    EnrollSpassComponent,
    EnrollRemoteComponent,
    EnrollSmsComponent,
    EnrollFoureyesComponent,
    EnrollApplspecComponent,
    EnrollDaypasswordComponent,
    EnrollEmailComponent,
    EnrollIndexedsecretComponent,
    EnrollPaperComponent,
    EnrollPushComponent,
    EnrollRegistrationComponent,
    EnrollTanComponent,
    EnrollTiqrComponent
  ],
  templateUrl: "./template-added-token-row.component.html",
  styleUrls: ["./template-added-token-row.component.scss"]
})
export class TemplateAddedTokenRowComponent {
  updateAdditionalFormFields($event: { [key: string]: FormControl<any> }) {
    this.formControls.set($event);
    for (const controlKey of Object.keys($event)) {
      const control = $event[controlKey];
      const patch: { [key: string]: any } = {};
      if (control) {
        patch[controlKey] = control.value;
        control.valueChanges.subscribe((newValue) => {
          this.updateToken({ [controlKey]: newValue });
        });
      }
      this._initialTokenFill(patch);
    }
  }

  private _initialTokenFill(patch: { [key: string]: any }) {
    // Fill the received patch into the token. But only missing values. Not overwriting existing ones.
    const token = this.token() as any;
    const updatedToken: { [key: string]: any } = {};
    for (const key of Object.keys(patch)) {
      if (token[key] === undefined || token[key] === null) {
        updatedToken[key] = patch[key];
      }
    }
    if (Object.keys(updatedToken).length > 0) {
      this.updateToken(updatedToken);
    }
  }

  constructor() {
    effect(() => {
      // Replace the default form control values with the token's current values
      const controls = this.formControls();
      const token = this.token() as any;
      for (const controlKey of Object.keys(controls)) {
        const control = controls[controlKey];
        if (control) {
          const tokenValue = token[controlKey];
          if (tokenValue !== undefined && tokenValue !== null && control.value !== tokenValue) {
            control.setValue(tokenValue, { emitEvent: false });
          }
        }
      }
    });
  }

  token = input.required<any>();
  index = input.required<number>();
  isEditMode = input.required<boolean>();
  @Output() onEditToken = new EventEmitter<any>();
  @Output() onRemoveToken = new EventEmitter<number>();

  getEnrollmentData = signal<
    | ((basicOptions: TokenEnrollmentData) => {
        data: TokenEnrollmentData;
        mapper: TokenApiPayloadMapper<TokenEnrollmentData>;
      } | null)
    | undefined
  >(undefined);
  formControls = signal<{ [key: string]: FormControl<any> }>({});

  childHadNoForm = computed(() => Object.keys(this.formControls()).length === 0);

  updateToken(patch: { [key: string]: any }) {
    this.onEditToken.emit({ ...patch });
  }
  removeToken() {
    if (this.index() < 0) return;
    this.onRemoveToken.emit(this.index());
  }
}
