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
import { Component, computed, inject, signal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatButton } from "@angular/material/button";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { EnrollmentPinComponent } from "@components/shared/enrollment-pin/enrollment-pin.component";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ERR, mustEqual, requiredNonBlank } from "@utils/form-rules.utils";
import { hasError, touchAll } from "@utils/form-state.utils";

@Component({
  selector: "app-attach-token-self-service",
  imports: [
    FormField,
    MatError,
    MatFormField,
    MatLabel,
    MatInput,
    MatButton,
    MatIcon,
    EnrollmentPinComponent,
    ScrollToTopDirective,
    StickyHeaderDirective
  ],
  templateUrl: "./assign-token-self-service.component.html",
  styleUrl: "./assign-token-self-service.component.scss"
})
export class AssignTokenSelfServiceComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private router = inject(Router);
  tokenSerial = this.tokenService.tokenSerial;
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;
  readonly serialModel = signal({ serial: "" });
  readonly setPinValue = signal("");
  readonly repeatPinValue = signal("");
  readonly serialForm = form(this.serialModel, (f) => {
    requiredNonBlank(f.serial);
  });
  readonly setPinForm = form(this.setPinValue);
  readonly repeatPinForm = form(this.repeatPinValue, (f) => {
    mustEqual(f, this.setPinValue);
  });
  readonly canAssign = computed(() => this.serialForm().valid() && this.repeatPinForm().valid());

  async assignUserToToken() {
    if (!this.canAssign()) {
      await Promise.all([touchAll(this.serialForm), touchAll(this.repeatPinForm)]);
      return;
    }
    const serial = this.serialModel().serial;
    this.tokenService
      .assignUser({
        tokenSerial: serial,
        username: "",
        realm: "",
        pin: this.setPinValue()
      })
      .subscribe({
        next: () => {
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + serial);
          this.tokenSerial.set(serial);
        }
      });
  }
}
