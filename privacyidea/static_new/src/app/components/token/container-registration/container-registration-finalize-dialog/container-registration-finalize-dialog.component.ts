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
import { Component, inject, Signal } from "@angular/core";
import { MatDialogContent } from "@angular/material/dialog";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContainerRegisterFinalizeData } from "../../container-details/container-details-actions/container-details-actions.component";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";

@Component({
  selector: "app-container-registration-finalize-dialog",
  templateUrl: "./container-registration-finalize-dialog.component.html",
  styleUrls: ["./container-registration-finalize-dialog.component.scss"],
  imports: [MatDialogContent, MatIcon, DialogWrapperComponent, MatButtonModule]
})
export class ContainerRegistrationFinalizeDialogComponent extends AbstractDialogComponent<
  Signal<ContainerRegisterFinalizeData | undefined>,
  void
> {
  get dialogTitle(): string {
    return this.data()?.rollover ? $localize`Container Rollover` : $localize`Register Container`;
  }
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);

  regenerateQRCode() {
    // other parameters are set by the container tab component to use the previously set values
    this.data()?.registerContainer(undefined, undefined, undefined, this.data()?.rollover, true);
  }
}
