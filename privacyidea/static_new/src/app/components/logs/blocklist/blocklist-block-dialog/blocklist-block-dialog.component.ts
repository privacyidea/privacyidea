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

// What the dialog hands back: a null duration means a block that does not expire.
export interface BlocklistBlockDialogResult {
  ip: string;
  durationSeconds: number | null;
}

// The duration is always sent in seconds; the unit only changes how it is entered.
type DurationUnit = "seconds" | "minutes" | "hours";

const DURATION_UNIT_FACTORS: Record<DurationUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600
};

@Component({
  selector: "app-blocklist-block-dialog",
  templateUrl: "./blocklist-block-dialog.component.html",
  styleUrls: ["./blocklist-block-dialog.component.scss"],
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
export class BlocklistBlockDialogComponent extends AbstractDialogComponent<void, BlocklistBlockDialogResult | null> {
  readonly ip = signal("");
  // Permanent by default, matching the user lock: an admin blocking by hand is reacting to an incident.
  readonly mode = signal<"permanent" | "timed">("permanent");
  readonly durationInput = signal("");
  readonly durationUnit = signal<DurationUnit>("minutes");
  readonly durationUnits: readonly DurationUnit[] = ["seconds", "minutes", "hours"];

  readonly durationSeconds = computed<number | null>(() => {
    const parsed = Number.parseInt(this.durationInput().trim(), 10);
    return Number.isNaN(parsed) || parsed <= 0 ? null : parsed * DURATION_UNIT_FACTORS[this.durationUnit()];
  });

  // The timed controls stay in the layout while "permanent" is selected so switching modes does not
  // shift the dialog; they are simply disabled until a timed block is chosen.
  readonly durationDisabled = computed<boolean>(() => this.mode() === "permanent");

  // Only the obviously-empty case is caught here; whether the address parses, and whether it is on the
  // never-block list, is the backend's answer and arrives as a notification.
  readonly canConfirm = computed<boolean>(
    () => this.ip().trim().length > 0 && (this.mode() === "permanent" || this.durationSeconds() !== null)
  );

  readonly dialogActions = computed((): DialogAction<string>[] => [
    {
      label: $localize`Block`,
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
    this.dialogRef.close({
      ip: this.ip().trim(),
      durationSeconds: this.mode() === "permanent" ? null : this.durationSeconds()
    });
  }
}
