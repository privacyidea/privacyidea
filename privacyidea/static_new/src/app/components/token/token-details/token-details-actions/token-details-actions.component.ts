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

import { Component, inject, Input, input, output, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatIconModule } from "@angular/material/icon";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ResyncTokenActionComponent } from "@components/token/token-details/token-details-actions/resync-token-action/resync-token-action.component";
import { SetPinActionComponent } from "@components/token/token-details/token-details-actions/set-pin-action/set-pin-action.component";
import { TestOtpPinActionComponent } from "@components/token/token-details/token-details-actions/test-otp-pin-action/test-otp-pin-action.component";
import { VerifyEnrollmentComponent } from "@components/token/token-details/token-details-actions/verify-enrollment/verify-enrollment.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TokenDetails } from "@services/token/token.service";

@Component({
  selector: "app-token-details-actions",
  standalone: true,
  imports: [
    FormsModule,
    MatButtonModule,
    MatDivider,
    MatIconModule,
    RouterLink,
    SetPinActionComponent,
    ResyncTokenActionComponent,
    TestOtpPinActionComponent,
    VerifyEnrollmentComponent
  ],
  templateUrl: "./token-details-actions.component.html",
  styleUrl: "./token-details-actions.component.scss"
})
export class TokenDetailsActionsComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() tokenType!: WritableSignal<string>;
  @Input() passkeyTestResult!: WritableSignal<{
    kind: "success" | "warning";
    message: string;
    mismatch?: { serial: string; username: string; realm?: string };
  } | null>;
  token = input<TokenDetails>();
  testPasskey = output<void>();
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
