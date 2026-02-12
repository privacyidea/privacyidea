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

import { Component, computed } from "@angular/core";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { CommonModule } from "@angular/common";
import { DialogAction } from "../../../../models/dialog";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import {
  AbstractControl,
  FormControl,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators
} from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { toSignal } from "@angular/core/rxjs-interop";
import { map } from "rxjs";

export function mustBeDifferentValidator(originalValue: string | null): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const isSame = control.value === originalValue;
    return isSame ? { notChanged: true } : null;
  };
}

@Component({
  selector: "app-copy-policy-dialog",
  templateUrl: "./copy-policy-dialog.component.html",
  styleUrls: ["./copy-policy-dialog.component.scss"],
  standalone: true,
  imports: [DialogWrapperComponent, CommonModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule]
})
export class CopyPolicyDialogComponent extends AbstractDialogComponent<string, string | null> {
  readonly nameControl = new FormControl(this.data, [Validators.required, mustBeDifferentValidator(this.data)]);

  readonly isInvalid = toSignal(this.nameControl.statusChanges.pipe(map(() => this.nameControl.invalid)), {
    initialValue: this.nameControl.invalid
  });

  readonly actions = computed<DialogAction<"submit" | null>[]>(() => [
    {
      label: $localize`Copy Policy`,
      value: "submit",
      type: "confirm",
      disabled: this.isInvalid()
    }
  ]);

  onAction(value: "submit" | null): void {
    if (value === "submit" && this.nameControl.valid) {
      setTimeout(() => {
        this.close(this.nameControl.value);
      });
    } else {
      setTimeout(() => {
        this.close(null);
      });
    }
  }
}
