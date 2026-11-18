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

import { Component, computed, inject } from "@angular/core";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { EnrollmentCustomizationFrameComponent } from "@components/token/token-enrollment/enrollment-customization-frame/enrollment-customization-frame.component";
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogAction } from "@models/dialog";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";

type WizardLastStepAction = "create_container" | "logout";

@Component({
  selector: "app-token-enrollment-last-step-dialog-wizard",
  templateUrl: "./token-enrollment-last-step-dialog.wizard.component.html",
  imports: [
    DialogWrapperComponent,
    EnrollmentCustomizationFrameComponent,
    TokenEnrollmentDataComponent,
    TokenEnrolledTextComponent
  ]
})
export class TokenEnrollmentLastStepDialogWizardComponent extends TokenEnrollmentLastStepDialogComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router = inject(Router);

  // Creating a container or logging out are the only ways on, so the dialog cannot be closed. Logout tells
  // the user that they are done. Logging out in between goes through the navigation.
  protected readonly actions = computed<DialogAction<WizardLastStepAction>[]>(() => {
    const blocked = !!this.closeBlockedReason();
    const actions: DialogAction<WizardLastStepAction>[] = [];
    if (this.authService.containerWizard().enabled) {
      actions.push({
        type: "auxiliary",
        label: $localize`:@@common.createContainer:Create Container`,
        value: "create_container",
        className: "button-width-m",
        disabled: blocked
      });
    }
    actions.push({
      type: "auxiliary",
      label: $localize`:@@common.logout:Logout`,
      value: "logout",
      primary: true,
      disabled: blocked
    });
    return actions;
  });

  constructor() {
    super();
    this.dialogRef.disableClose = true;
  }

  onAction(action: WizardLastStepAction): void {
    if (action === "create_container") {
      this.dialogRef.close();
      this.router.navigate([ROUTE_PATHS.CONTAINERS_WIZARD]);
      return;
    }
    this.authService.logout();
  }
}
