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

import { Component, computed, DestroyRef, effect, inject, input, linkedSignal, output, signal } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormControl, FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData,
  TokenEnrollmentPayload
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { getTokenApiPayloadMapper } from "@app/mappers/token-api-payload/token-api-payload-mapper-registry";
import { EnrollApplspecComponent } from "@components/token/token-enrollment/enroll-asp/enroll-applspec.component";
import { EnrollDaypasswordComponent } from "@components/token/token-enrollment/enroll-daypassword/enroll-daypassword.component";
import { EnrollEmailComponent } from "@components/token/token-enrollment/enroll-email/enroll-email.component";
import { EnrollFoureyesComponent } from "@components/token/token-enrollment/enroll-foureyes/enroll-foureyes.component";
import { EnrollHotpComponent } from "@components/token/token-enrollment/enroll-hotp/enroll-hotp.component";
import { EnrollIndexedsecretComponent } from "@components/token/token-enrollment/enroll-indexsecret/enroll-indexedsecret.component";
import { EnrollPaperComponent } from "@components/token/token-enrollment/enroll-paper/enroll-paper.component";
import { EnrollPushComponent } from "@components/token/token-enrollment/enroll-push/enroll-push.component";
import { EnrollRegistrationComponent } from "@components/token/token-enrollment/enroll-registration/enroll-registration.component";
import { EnrollRemoteComponent } from "@components/token/token-enrollment/enroll-remote/enroll-remote.component";
import { EnrollSmsComponent } from "@components/token/token-enrollment/enroll-sms/enroll-sms.component";
import { EnrollSpassComponent } from "@components/token/token-enrollment/enroll-spass/enroll-spass.component";
import { EnrollTanComponent } from "@components/token/token-enrollment/enroll-tan/enroll-tan.component";
import { EnrollTiqrComponent } from "@components/token/token-enrollment/enroll-tiqr/enroll-tiqr.component";
import { EnrollTotpComponent } from "@components/token/token-enrollment/enroll-totp/enroll-totp.component";
import { enrollmentArgsGetterFn } from "@components/token/token-enrollment/token-enrollment.component";

@Component({
  selector: "app-template-added-token-row",
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatExpansionModule,
    FormsModule,
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
  private readonly destroyRef = inject(DestroyRef);

  // Inputs & Outputs
  readonly tokenEnrollmentPayload = input.required<TokenEnrollmentPayload>();

  readonly index = input.required<number>();
  readonly onEditToken = output<Partial<TokenEnrollmentPayload>>();
  readonly onRemoveToken = output<number>();

  // State Signals
  readonly userAssign = linkedSignal(() => this.tokenEnrollmentPayload().user === true);

  readonly formControls = signal<{ [key: string]: FormControl<any> }>({});
  readonly childHadNoForm = computed(() => Object.keys(this.formControls()).length === 0);

  readonly enrollmentArgsGetterSignal = signal<enrollmentArgsGetterFn | null>(null);

  readonly tokenEnrollmentData = linkedSignal<any, Partial<TokenEnrollmentData> | null>({
    source: () => ({
      payload: this.tokenEnrollmentPayload(),
      enrollmentArgsGetter: this.enrollmentArgsGetterSignal()
    }),
    computation: (source) => {
      const mapper = getTokenApiPayloadMapper(source.payload?.type);
      if (!mapper) return null;
      const enrollmentData = mapper.fromApiPayload(source.payload);
      return enrollmentData;
    }
  });

  constructor() {
    // Sync external token changes back into the form controls
    effect(() => {
      const controls = this.formControls();
      const currentToken = this.tokenEnrollmentPayload();

      Object.entries(controls).forEach(([key, control]) => {
        const tokenValue = (currentToken as any)[key];
        if (tokenValue !== undefined && tokenValue !== null && control.value !== tokenValue) {
          control.setValue(tokenValue, { emitEvent: false });
        }
      });
    });
  }

  updateEnrollmentArgsGetter(
    enrollmentArgsGetter: (
      basicOptions: TokenEnrollmentData
    ) => { data: TokenEnrollmentData; mapper: TokenApiPayloadMapper<TokenEnrollmentData> } | null
  ) {
    this.enrollmentArgsGetterSignal.set(enrollmentArgsGetter);
    this.updateToken(this.tokenEnrollmentData() ?? {});
  }

  // Token Management Methods
  updateAdditionalFormFields(fields: { [key: string]: FormControl<any> }) {
    this.formControls.set(fields);
    const initialPatch: { [key: string]: any } = {};

    Object.entries(fields).forEach(([key, control]) => {
      if (control) {
        initialPatch[key] = control.value;

        control.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((value) => {
          if (value === this.tokenEnrollmentData()?.[key]) {
            return;
          }
          this.updateToken({ [key]: value });
        });
      }
    });

    this._initialTokenFill(initialPatch);
  }

  toggleUserAssign(checked: boolean) {
    this.userAssign.set(checked);
    this.onEditToken.emit({ user: checked });
  }

  removeToken() {
    if (this.index() >= 0) {
      this.onRemoveToken.emit(this.index());
    }
  }

  private updateToken(enrollmentData: Partial<TokenEnrollmentData>) {
    const updatedEnrollmentData = { ...this.tokenEnrollmentData(), ...enrollmentData };

    this.tokenEnrollmentData.set(updatedEnrollmentData);
    const getter = this.enrollmentArgsGetterSignal();
    if (!getter) {
      return;
    }
    const args = getter({
      type: this.tokenEnrollmentPayload().type,
      ...updatedEnrollmentData
    });
    if (args) {
      const mappedData = args.mapper.toApiPayload(args.data);
      this.onEditToken.emit(mappedData);
    }
  }

  private _initialTokenFill(patch: { [key: string]: Partial<TokenEnrollmentData> }) {
    const currentToken = this.tokenEnrollmentData();
    const updatedFields: { [key: string]: Partial<TokenEnrollmentData> } = {};

    Object.keys(patch).forEach((key) => {
      if ((currentToken as any)[key] === undefined || (currentToken as any)[key] === null) {
        updatedFields[key] = patch[key];
      }
    });

    if (Object.keys(updatedFields).length > 0) {
      this.updateToken(updatedFields);
    }
  }
}
