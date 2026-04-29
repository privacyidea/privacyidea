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
import { NgClass } from "@angular/common";
import { Component, inject } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatButton, MatIconButton } from "@angular/material/button";
import { DateAdapter, MAT_DATE_FORMATS, MatNativeDateModule, provideNativeDateAdapter } from "@angular/material/core";
import { MatDatepickerModule } from "@angular/material/datepicker";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MAT_TOOLTIP_DEFAULT_OPTIONS, MatTooltip } from "@angular/material/tooltip";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { EnrollTokenTypeSwitchComponent } from "../../shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { EnrollmentPinComponent } from "../../shared/enrollment-pin/enrollment-pin.component";
import {
  CUSTOM_DATE_FORMATS,
  CUSTOM_TOOLTIP_OPTIONS,
  CustomDateAdapter,
  TokenEnrollmentComponent
} from "./token-enrollment.component";
import { TokenEnrollmentLastStepDialogSelfServiceComponent } from "./token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component";
import { EnrollmentResponse } from "../../../mappers/token-api-payload/_token-api-payload.mapper";

@Component({
  selector: "app-token-enrollment-self-service",
  imports: [
    MatFormField,
    MatSelect,
    MatOption,
    ReactiveFormsModule,
    FormsModule,
    MatInput,
    MatLabel,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatNativeDateModule,
    MatDatepickerModule,
    MatButton,
    MatIcon,
    MatIconButton,
    NgClass,
    MatError,
    MatTooltip,
    ClearableInputComponent,
    ScrollToTopDirective,
    MatHint,
    EnrollTokenTypeSwitchComponent,
    EnrollmentPinComponent
  ],
  templateUrl: "./token-enrollment.self-service.component.html",
  styleUrl: "./token-enrollment.component.scss",
  providers: [
    provideNativeDateAdapter(),
    { provide: DateAdapter, useFactory: () => new CustomDateAdapter("+00:00") },
    { provide: MAT_DATE_FORMATS, useValue: CUSTOM_DATE_FORMATS },
    { provide: MAT_TOOLTIP_DEFAULT_OPTIONS, useValue: CUSTOM_TOOLTIP_OPTIONS }
  ]
})
export class TokenEnrollmentSelfServiceComponent extends TokenEnrollmentComponent {
  protected override containerService: ContainerServiceInterface = inject(ContainerService);
  protected override realmService: RealmServiceInterface = inject(RealmService);
  protected override notificationService: NotificationServiceInterface = inject(NotificationService);
  protected override userService: UserServiceInterface = inject(UserService);
  protected override tokenService: TokenServiceInterface = inject(TokenService);
  protected override versioningService: VersioningServiceInterface = inject(VersioningService);
  protected override contentService: ContentServiceInterface = inject(ContentService);
  protected override dialogService: DialogServiceInterface = inject(DialogService);

  constructor() {
    super();
  }

  protected override openLastStepDialog(response: EnrollmentResponse | null): void {
    if (!response) {
      this.notificationService.openSnackBar("No enrollment response available.");
      return;
    }

    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: response
    });

    this.dialogService.openDialog({
      component: TokenEnrollmentLastStepDialogSelfServiceComponent,
      data: this.enrolledDialogData()
    });
  }
}
