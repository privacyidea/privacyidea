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
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogAction } from "@models/dialog";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TokenEnrollmentSuccessComponent } from "./token-enrollment-success.component";

type WizardLastStepAction = "create_container" | "logout";

@Component({
  selector: "app-token-enrollment-success-wizard",
  templateUrl: "./token-enrollment-success.wizard.component.html",
  imports: [TokenEnrollmentDataComponent]
})
export class TokenEnrollmentSuccessWizardComponent extends TokenEnrollmentSuccessComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router = inject(Router);

  // The only ways on: the dialog cannot be closed, and Logout tells the user that they are done.
  override readonly closable = false;
  override readonly actions = computed<DialogAction<WizardLastStepAction>[]>(() => {
    const actions: DialogAction<WizardLastStepAction>[] = [];
    if (this.authService.containerWizard().enabled) {
      actions.push({
        type: "auxiliary",
        label: $localize`:@@common.createContainer:Create Container`,
        value: "create_container",
        className: "button-width-m"
      });
    }
    actions.push({
      type: "auxiliary",
      label: $localize`:@@common.logout:Logout`,
      value: "logout",
      primary: true
    });
    return actions;
  });

  override onAction(action: WizardLastStepAction): void {
    const label = this.actions().find((candidate) => candidate.value === action)?.label;
    this.confirmClose(label).subscribe((confirmed) => {
      if (!confirmed) {
        return;
      }
      if (action === "create_container") {
        this.flow.close();
        this.router.navigate([ROUTE_PATHS.CONTAINERS_WIZARD]);
        return;
      }
      this.authService.logout();
    });
  }
}
