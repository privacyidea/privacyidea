import { Component, effect, EventEmitter, input, Input, linkedSignal, Output, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { ContainerTemplateToken } from "../../../../services/container/container.service";
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
import { HotpEnrollmentData } from "../../../../mappers/token-api-payload/hotp-token-api-payload.mapper";

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
  updateClickEnroll(
    $event: (
      basicOptions: TokenEnrollmentData
    ) => { data: TokenEnrollmentData; mapper: TokenApiPayloadMapper<TokenEnrollmentData> } | null
  ) {
    this.onClickEnroll.set($event);
  }
  updateAdditionalFormFields($event: { [key: string]: FormControl<any> }) {
    this.formControls.set($event);
    for (const controlKey of Object.keys($event)) {
      console.log("Form Control Key:", controlKey);
      const control = $event[controlKey];
      const patch: { [key: string]: any } = {};
      if (control) {
        patch[controlKey] = control.value;
        console.log("Form Control Value:", control.value);
        control.valueChanges.subscribe((newValue) => {
          console.log(`Form Control '${controlKey}' Value Changed:`, newValue);
        });
      }
      this.updateToken(patch);
    }
  }
  token = input.required<ContainerTemplateToken>();
  index = input.required<number>();
  isEditMode = input.required<boolean>();
  @Output() onEditToken = new EventEmitter<ContainerTemplateToken>();
  @Output() onDelete = new EventEmitter<number>();

  onClickEnroll = signal<
    | ((basicOptions: TokenEnrollmentData) => {
        data: TokenEnrollmentData;
        mapper: TokenApiPayloadMapper<TokenEnrollmentData>;
      } | null)
    | undefined
  >(undefined);
  formControls = signal<{ [key: string]: FormControl<any> }>({});

  updateToken(patch: Partial<ContainerTemplateToken>) {
    if (!this.isEditMode()) return;
    this.onEditToken.emit({ ...this.token(), ...patch });
  }
  deleteToken() {
    this.onDelete.emit(this.index());
  }
}
