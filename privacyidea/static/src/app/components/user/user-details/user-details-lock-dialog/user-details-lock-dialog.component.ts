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
import { Component, computed, signal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatDialogModule } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatRadioModule } from "@angular/material/radio";
import { MatSelectModule } from "@angular/material/select";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import {
  DURATION_UNITS,
  DurationFormModel,
  durationRules,
  POSITIVE_INTEGER_ERROR,
  selectedDurationSeconds
} from "@utils/duration-unit.utils";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

export interface UserDetailsLockDialogData {
  username: string;
  realm: string;
}

// What the dialog hands back: null means a lock that does not expire, which is the default.
export interface UserDetailsLockDialogResult {
  durationSeconds: number | null;
}

@Component({
  selector: "app-user-details-lock-dialog",
  templateUrl: "./user-details-lock-dialog.component.html",
  styleUrls: ["./user-details-lock-dialog.component.scss"],
  standalone: true,
  imports: [
    FormField,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
    MatSelectModule,
    DialogWrapperComponent
  ]
})
export class UserDetailsLockDialogComponent extends AbstractDialogComponent<
  UserDetailsLockDialogData,
  UserDetailsLockDialogResult | null
> {
  // Permanent by default: an admin locking by hand is normally reacting to an incident, so a lock that
  // lifts on its own would be the surprising outcome.
  readonly lockModel = signal<DurationFormModel>({ mode: "permanent", durationInput: null, durationUnit: "minutes" });
  // The timed controls stay in the layout while "permanent" is selected so switching modes does not
  // shift the dialog; the rules disable them until a timed lock is chosen.
  readonly lockForm = form(this.lockModel, (f) => durationRules(f.mode, f.durationInput, f.durationUnit));
  readonly durationUnits = DURATION_UNITS;
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  protected readonly POSITIVE_INTEGER_ERROR = POSITIVE_INTEGER_ERROR;

  readonly dialogActions = computed((): DialogAction<string>[] => [
    {
      label: $localize`:@@user.lock:Lock`,
      value: "confirm",
      type: "confirm",
      disabled: !this.lockForm().valid(),
      primary: true
    }
  ]);

  onAction(actionValue: string): void {
    if (actionValue !== "confirm" || !this.lockForm().valid()) {
      return;
    }
    this.dialogRef.close({ durationSeconds: selectedDurationSeconds(this.lockModel()) });
  }
}
