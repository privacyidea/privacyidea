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
import { Component, inject, input, OnInit, signal, output } from '@angular/core';
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import {
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface,
  RemoteServer
} from "@services/privacyidea-server/privacyidea-server.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  RemoteApiPayloadMapper,
  RemoteEnrollmentData
} from "@app/mappers/token-api-payload/remote-token-api-payload.mapper";

@Component({
  selector: "app-enroll-remote",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatCheckbox,
    MatError,
    FormField
  ],
  templateUrl: "./enroll-remote.component.html"
})
export class EnrollRemoteComponent implements OnInit {
  protected readonly enrollmentMapper = inject(RemoteApiPayloadMapper);
  protected readonly privacyideaServerService: PrivacyideaServerServiceInterface = inject(PrivacyideaServerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  enrollmentData = input<RemoteEnrollmentData>();
  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<(basicOptions: TokenEnrollmentData) => {
      data: RemoteEnrollmentData;
      mapper: TokenApiPayloadMapper<RemoteEnrollmentData>;
    } | null>();
  disabled = input<boolean>(false);

  checkPinLocally = signal<boolean>(false);
  remoteServer = signal<RemoteServer | null>(null);
  remoteSerial = signal<string>("");
  remoteUser = signal<string>("");
  remoteRealm = signal<string>("");
  remoteResolver = signal<string>("");

  remoteSerialForm = form(this.remoteSerial, (f) => {
    required(f);
    disabled(f, () => this.disabled());
  });
  remoteUserForm = form(this.remoteUser, (f) => {
    required(f);
    disabled(f, () => this.disabled());
  });
  remoteResolverForm = form(this.remoteResolver, (f) => {
    required(f);
    disabled(f, () => this.disabled());
  });
  remoteRealmForm = form(this.remoteRealm, (f) => {
    disabled(f, () => this.disabled());
  });

  remoteServerOptions = this.privacyideaServerService.remoteServerOptions;

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.checkPinLocally.set(this.enrollmentData()?.checkPinLocally ?? false);
      this.remoteServer.set(this.enrollmentData()?.remoteServer ?? null);
      this.remoteSerial.set(this.enrollmentData()?.remoteSerial ?? "");
      this.remoteUser.set(this.enrollmentData()?.remoteUser ?? "");
      this.remoteRealm.set(this.enrollmentData()?.remoteRealm ?? "");
      this.remoteResolver.set(this.enrollmentData()?.remoteResolver ?? "");
    }
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: RemoteEnrollmentData;
    mapper: TokenApiPayloadMapper<RemoteEnrollmentData>;
  } | null => {
    if (!this.remoteServer()) {
      return null;
    }
    if (
      !this.remoteSerialForm().valid() ||
      !this.remoteUserForm().valid() ||
      !this.remoteResolverForm().valid()
    ) {
      this.remoteSerialForm().markAsTouched();
      this.remoteUserForm().markAsTouched();
      this.remoteResolverForm().markAsTouched();
      return null;
    }

    const enrollmentData: RemoteEnrollmentData = {
      ...basicOptions,
      type: "remote",
      checkPinLocally: this.checkPinLocally(),
      remoteServer: this.remoteServer(),
      remoteSerial: this.remoteSerial(),
      remoteUser: this.remoteUser(),
      remoteRealm: this.remoteRealm(),
      remoteResolver: this.remoteResolver()
    };

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
