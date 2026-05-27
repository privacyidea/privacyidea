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
import { form, FormField, validate } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatDialogModule } from "@angular/material/dialog";
import { MatInputModule } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { MachineService, MachineServiceInterface } from "@services/machine/machine.service";
import { Observable } from "rxjs";

export interface HotpMachineAssignDialogData {
  tokenSerial: string;
}

@Component({
  selector: "token-ssh-machine-attach-dialog",
  styleUrls: ["./token-hotp-machine-attach-dialog.component.scss"],
  templateUrl: "./token-hotp-machine-attach-dialog.component.html",
  standalone: true,
  imports: [
    FormField,
    MatInputModule,
    MatButtonModule,
    MatDialogModule,
    DialogWrapperComponent
  ]
})
export class TokenHotpMachineAssignDialogComponent extends AbstractDialogComponent<
  HotpMachineAssignDialogData,
  Observable<any> | null
> {
  private machineService: MachineServiceInterface = inject(MachineService);
  public tokenSerial = this.data.tokenSerial;

  assignAction: DialogAction<string> = {
    label: "Assign",
    value: "assign",
    type: "confirm",
    primary: true
  };
  onAction(actionValue: string): void {
    if (actionValue === "assign") {
      this.onAssign();
    }
  }

  countValue = signal("100");
  countForm = form(this.countValue, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      const numericValue = Number(value);
      if (!value || isNaN(numericValue)) return [{ kind: "required" as any }];
      if (numericValue < 10) return [{ kind: "min" as any }];
      return [];
    });
  });

  roundsValue = signal("10000");
  roundsForm = form(this.roundsValue, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      const numericValue = Number(value);
      if (!value || isNaN(numericValue)) return [{ kind: "required" as any }];
      if (numericValue < 1000) return [{ kind: "min" as any }];
      return [];
    });
  });

  isFormValid = computed(() => this.countForm().valid() && this.roundsForm().valid());

  onAssign() {
    if (!this.isFormValid()) return;

    const request = this.machineService.postAssignMachineToToken({
      application: "offline",
      count: Number(this.countValue()),
      machineid: 0,
      resolver: "",
      rounds: Number(this.roundsValue()),
      serial: this.data.tokenSerial
    });
    request.subscribe({
      next: (_) => {
        // Subscribed to ensure that the request will be executed
      },
      error: (error) => {
        console.error("Error during assignment request:", error);
      }
    });
    this.dialogRef.close(request);
  }
}
