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
import { Component, computed, signal, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatDialogModule } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";

@Component({
  selector: "app-user-details-pin-dialog",
  templateUrl: "./user-details-pin-dialog.component.html",
  styleUrls: ["./user-details-pin-dialog.component.scss"],
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    DialogWrapperComponent
  ]
})
export class UserDetailsPinDialogComponent extends AbstractDialogComponent<void, string | null> {
  pin = signal("");
  pinRepeat = signal("");
  hidePin = signal(true);
  pinsMatch = computed(() => this.pin() === this.pinRepeat());

  dialogActions = computed((): DialogAction<string>[] => {
    return [
      {
        label: "Confirm",
        value: "confirm",
        type: "confirm",
        disabled: !this.pinsMatch(),
        primary: true
      }
    ];
  });

  togglePinVisibility(): void {
    this.hidePin.update((prev) => !prev);
  }

  onAction(actionValue: string): void {
    if (actionValue === "confirm" && this.pinsMatch()) {
      this.dialogRef.close(this.pin());
    }
  }
}
