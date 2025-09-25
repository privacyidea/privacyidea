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
import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { ErrorStateMatcher, MatOption } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import {
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface,
  RemoteServer
} from "../../../../services/privavyidea-server/privacyidea-server.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  RemoteApiPayloadMapper,
  RemoteEnrollmentData
} from "../../../../mappers/token-api-payload/remote-token-api-payload.mapper";

export class RemoteErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value.id === "" : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-remote",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatOption,
    MatSelect,
    MatCheckbox,
    MatError
  ],
  templateUrl: "./enroll-remote.component.html",
  styleUrl: "./enroll-remote.component.scss"
})
export class EnrollRemoteComponent implements OnInit {
  protected readonly enrollmentMapper: RemoteApiPayloadMapper = inject(RemoteApiPayloadMapper);
  protected readonly privacyideaServerService: PrivacyideaServerServiceInterface = inject(PrivacyideaServerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  checkPinLocallyControl = new FormControl<boolean>(false, [Validators.required]);
  remoteServerControl = new FormControl<RemoteServer | null>(null, [Validators.required]);
  remoteSerialControl = new FormControl<string>("");
  remoteUserControl = new FormControl<string>("");
  remoteRealmControl = new FormControl<string>("");
  remoteResolverControl = new FormControl<string>("");

  remoteForm = new FormGroup({
    checkPinLocally: this.checkPinLocallyControl,
    remoteServer: this.remoteServerControl,
    remoteSerial: this.remoteSerialControl,
    remoteUser: this.remoteUserControl,
    remoteRealm: this.remoteRealmControl,
    remoteResolver: this.remoteResolverControl
  });

  remoteServerOptions = this.privacyideaServerService.remoteServerOptions;
  remoteErrorStateMatcher = new RemoteErrorStateMatcher();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      checkPinLocally: this.checkPinLocallyControl,
      remoteServer: this.remoteServerControl,
      remoteSerial: this.remoteSerialControl,
      remoteUser: this.remoteUserControl,
      remoteRealm: this.remoteRealmControl,
      remoteResolver: this.remoteResolverControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (
      this.remoteServerControl.invalid ||
      this.remoteSerialControl.invalid ||
      this.remoteUserControl.invalid ||
      this.remoteRealmControl.invalid ||
      this.remoteResolverControl.invalid ||
      this.checkPinLocallyControl.invalid
    ) {
      this.remoteForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: RemoteEnrollmentData = {
      ...basicOptions,
      type: "remote",
      checkPinLocally: !!this.checkPinLocallyControl.value,
      remoteServer: this.remoteServerControl.value,
      remoteSerial: this.remoteSerialControl.value ?? "",
      remoteUser: this.remoteUserControl.value ?? "",
      remoteRealm: this.remoteRealmControl.value ?? "",
      remoteResolver: this.remoteResolverControl.value ?? ""
    };

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
