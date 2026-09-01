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
import { MatButtonModule } from "@angular/material/button";
import { MatDialogModule } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatRadioModule } from "@angular/material/radio";
import { MatSelectModule } from "@angular/material/select";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";

export interface UserDetailsLockDialogData {
  username: string;
  realm: string;
}

// What the dialog hands back: null means a lock that does not expire, which is the default.
export interface UserDetailsLockDialogResult {
  durationSeconds: number | null;
}

// The duration is always sent in seconds; the unit only changes how it is entered. Mirrors the policy
// editor's action duration field.
type DurationUnit = "seconds" | "minutes" | "hours";

const DURATION_UNIT_FACTORS: Record<DurationUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600
};

@Component({
  selector: "app-user-details-lock-dialog",
  templateUrl: "./user-details-lock-dialog.component.html",
  styleUrls: ["./user-details-lock-dialog.component.scss"],
  standalone: true,
  imports: [
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
  readonly mode = signal<"permanent" | "timed">("permanent");
  readonly durationInput = signal("");
  readonly durationUnit = signal<DurationUnit>("minutes");
  readonly durationUnits: readonly DurationUnit[] = ["seconds", "minutes", "hours"];

  readonly durationSeconds = computed<number | null>(() => {
    const parsed = Number.parseInt(this.durationInput().trim(), 10);
    return Number.isNaN(parsed) || parsed <= 0 ? null : parsed * DURATION_UNIT_FACTORS[this.durationUnit()];
  });

  // The timed controls stay in the layout while "permanent" is selected so switching modes does not
  // shift the dialog; they are simply disabled until a timed lock is chosen.
  readonly durationDisabled = computed<boolean>(() => this.mode() === "permanent");

  // A timed lock needs a duration the backend would accept; a permanent one needs nothing.
  readonly canConfirm = computed<boolean>(() => this.mode() === "permanent" || this.durationSeconds() !== null);

  readonly dialogActions = computed((): DialogAction<string>[] => [
    {
      label: $localize`Lock`,
      value: "confirm",
      type: "confirm",
      disabled: !this.canConfirm(),
      primary: true
    }
  ]);

  onAction(actionValue: string): void {
    if (actionValue !== "confirm" || !this.canConfirm()) {
      return;
    }
    this.dialogRef.close({ durationSeconds: this.mode() === "permanent" ? null : this.durationSeconds() });
  }
}
