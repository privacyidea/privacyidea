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
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

// What the dialog hands back: a null duration means a block that does not expire.
export interface BlocklistBlockDialogResult {
  ip: string;
  durationSeconds: number | null;
}

interface BlocklistBlockFormModel extends DurationFormModel {
  ip: string;
}

@Component({
  selector: "app-blocklist-block-dialog",
  templateUrl: "./blocklist-block-dialog.component.html",
  styleUrls: ["./blocklist-block-dialog.component.scss"],
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
export class BlocklistBlockDialogComponent extends AbstractDialogComponent<void, BlocklistBlockDialogResult | null> {
  // Permanent by default, matching the user lock: an admin blocking by hand is reacting to an incident.
  readonly blockModel = signal<BlocklistBlockFormModel>({
    ip: "",
    mode: "permanent",
    durationInput: null,
    durationUnit: "minutes"
  });
  // Only the obviously-empty address is caught here; whether it parses, and whether it is on the
  // never-block list, is the backend's answer and arrives as a notification. The timed controls stay in the
  // layout while "permanent" is selected so switching modes does not shift the dialog; the rules disable them
  // until a timed block is chosen.
  readonly blockForm = form(this.blockModel, (f) => {
    requiredNonBlank(f.ip);
    durationRules(f.mode, f.durationInput, f.durationUnit);
  });
  readonly durationUnits = DURATION_UNITS;
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  protected readonly POSITIVE_INTEGER_ERROR = POSITIVE_INTEGER_ERROR;

  readonly dialogActions = computed((): DialogAction<string>[] => [
    {
      label: $localize`:@@blocklist.block:Block`,
      value: "confirm",
      type: "confirm",
      disabled: !this.blockForm().valid(),
      primary: true
    }
  ]);

  onAction(actionValue: string): void {
    if (actionValue !== "confirm" || !this.blockForm().valid()) {
      return;
    }
    const model = this.blockModel();
    this.dialogRef.close({ ip: model.ip.trim(), durationSeconds: selectedDurationSeconds(model) });
  }
}
