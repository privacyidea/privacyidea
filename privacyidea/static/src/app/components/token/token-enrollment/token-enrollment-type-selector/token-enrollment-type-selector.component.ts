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
import { Component, HostBinding, inject, input, output } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatOption, MatSelect } from "@angular/material/select";
import { MAT_TOOLTIP_DEFAULT_OPTIONS, MatTooltipModule } from "@angular/material/tooltip";
import { GridSelectNavDirective } from "@components/shared/directives/grid-select-nav.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TokenService, TokenServiceInterface, TokenType } from "@services/token/token.service";
import { TooltipAriaLabelDirective } from "@components/shared/directives/tooltip-aria-label.directive";
import { tokenTypeDisplayDescription, tokenTypeDisplayLabel, tokenTypes } from "@utils/token.utils";
import { CUSTOM_TOOLTIP_OPTIONS } from "../token-enrollment.constants";

@Component({
  selector: "app-token-enrollment-type-selector",
  templateUrl: "./token-enrollment-type-selector.component.html",
  styleUrl: "./token-enrollment-type-selector.component.scss",
  standalone: true,
  imports: [
    TooltipAriaLabelDirective,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    MatButton,
    MatIconButton,
    MatIcon,
    NgClass,
    MatTooltipModule,
    StickyHeaderDirective,
    GridSelectNavDirective
  ],
  providers: [{ provide: MAT_TOOLTIP_DEFAULT_OPTIONS, useValue: CUSTOM_TOOLTIP_OPTIONS }]
})
export class TokenEnrollmentTypeSelectorComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  @HostBinding("class.is-admin") get isAdmin(): boolean {
    return this.authService.role() === "admin";
  }

  scrollContainer = input.required<HTMLElement>();
  formInvalid = input<boolean>(false);
  enrollBlockedReason = input<string | null>(null);
  canReopenDialog = input<boolean>(false);
  reopenDialog = output<void>();

  protected readonly unsupportedTypeHint = $localize`:@@token.enrollmentUnsupportedType:Enrollment is not available for this token type.`;

  // A type the backend offers but this UI has no enroll component for, which is what a token
  // class added through PI_TOKEN_MODULES looks like from here.
  protected unsupported(type: TokenType): boolean {
    return !tokenTypes.some((known) => known.key === type.key);
  }

  protected label(type: TokenType): string {
    return tokenTypeDisplayLabel(type.info, type.name);
  }

  protected description(type: TokenType): string {
    return tokenTypeDisplayDescription(type.info);
  }
}
