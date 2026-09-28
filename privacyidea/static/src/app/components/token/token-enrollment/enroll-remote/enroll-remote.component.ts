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
import { Component, computed, forwardRef, inject, input, OnInit, signal } from "@angular/core";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import {
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface
} from "@services/privacyidea-server/privacyidea-server.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  RemoteApiPayloadMapper,
  RemoteEnrollmentData
} from "@app/mappers/token-api-payload/remote-token-api-payload.mapper";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";

@Component({
  selector: "app-enroll-remote",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, MatOption, MatSelect, MatCheckbox, MatError, MatTooltip, FormField],
  templateUrl: "./enroll-remote.component.html",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollRemoteComponent) }]
})
export class EnrollRemoteComponent extends EnrollTokenBase<RemoteEnrollmentData> implements OnInit {
  protected readonly enrollmentMapper: RemoteApiPayloadMapper = inject(RemoteApiPayloadMapper);
  protected readonly privacyideaServerService: PrivacyideaServerServiceInterface = inject(PrivacyideaServerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  enrollmentData = input<RemoteEnrollmentData>();
  disabled = input<boolean>(false);

  checkPinLocally = signal<boolean>(false);
  remoteServerId = signal<string>("");
  remoteSerial = signal<string>("");
  remoteUser = signal<string>("");
  remoteRealm = signal<string>("");
  remoteResolver = signal<string>("");

  remoteServerIdForm = form(this.remoteServerId, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !this.privacyideaServerService.canListRemoteServers());
  });
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

  // A server id handed in via enrollmentData (e.g. a rollover) still allows enrolling without the list.
  override readonly enrollmentBlockedReason = computed<string | null>(() =>
    !this.privacyideaServerService.canListRemoteServers() && !this.remoteServerId()
      ? $localize`:@@token.remoteServerNeedsReadRight:Remote tokens cannot be enrolled: selecting the remote server needs the privacyideaserver_read right.`
      : null
  );

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.checkPinLocally.set(this.enrollmentData()?.checkPinLocally ?? false);
      this.remoteServerId.set(this.enrollmentData()?.remoteServerId ?? "");
      this.remoteSerial.set(this.enrollmentData()?.remoteSerial ?? "");
      this.remoteUser.set(this.enrollmentData()?.remoteUser ?? "");
      this.remoteRealm.set(this.enrollmentData()?.remoteRealm ?? "");
      this.remoteResolver.set(this.enrollmentData()?.remoteResolver ?? "");
    }
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<RemoteEnrollmentData> | null {
    // A disabled field counts as valid, so the required check below would let an empty server through.
    if (this.enrollmentBlockedReason()) {
      return null;
    }
    if (
      !this.remoteServerIdForm().valid() ||
      !this.remoteSerialForm().valid() ||
      !this.remoteUserForm().valid() ||
      !this.remoteResolverForm().valid()
    ) {
      this.remoteServerIdForm().markAsTouched();
      this.remoteSerialForm().markAsTouched();
      this.remoteUserForm().markAsTouched();
      this.remoteResolverForm().markAsTouched();
      return null;
    }

    const enrollmentData: RemoteEnrollmentData = {
      ...basicOptions,
      type: "remote",
      checkPinLocally: this.checkPinLocally(),
      remoteServerId: this.remoteServerId(),
      remoteSerial: this.remoteSerial(),
      remoteUser: this.remoteUser(),
      remoteRealm: this.remoteRealm(),
      remoteResolver: this.remoteResolver()
    };

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
