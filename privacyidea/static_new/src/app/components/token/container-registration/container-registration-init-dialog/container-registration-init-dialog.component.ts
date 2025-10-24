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
import {Component, inject, ViewChild} from "@angular/core";
import {
    MAT_DIALOG_DATA,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle
} from "@angular/material/dialog";
import {
    ContainerRegistrationConfigComponent
} from "../container-registration-config/container-registration-config.component";
import {MatButton} from "@angular/material/button";

@Component({
    selector: "app-container-registration-init-dialog",
    templateUrl: "./container-registration-init-dialog.component.html",
    styleUrls: ["./container-registration-init-dialog.component.scss"],
    imports: [
        MatDialogTitle,
        MatDialogActions,
        MatDialogContent,
        ContainerRegistrationConfigComponent,
        MatButton,
        MatDialogClose
    ]
})
export class ContainerRegistrationInitDialogComponent {
    public readonly data = inject(MAT_DIALOG_DATA);

    @ViewChild(ContainerRegistrationConfigComponent)
    registrationConfigComponent!: ContainerRegistrationConfigComponent;

    onRegister() {
        this.data.registerContainer(
            this.registrationConfigComponent.userStorePassphrase,
            this.registrationConfigComponent.passphrasePrompt,
            this.registrationConfigComponent.passphraseResponse,
            this.data.rollover);
    }
}