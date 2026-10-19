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

import { Component, computed, effect, inject, signal } from "@angular/core";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";

import { form, FormField, validate } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogAction } from "@models/dialog";
import { PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";

@Component({
  selector: "app-copy-policy-dialog",
  templateUrl: "./copy-policy-dialog.component.html",
  styleUrls: ["./copy-policy-dialog.component.scss"],
  standalone: true,
  imports: [DialogWrapperComponent, FormField, MatFormFieldModule, MatInputModule]
})
export class CopyPolicyDialogComponent extends AbstractDialogComponent<string, string | null> {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly nameSignal = signal(this.data ?? "");
  readonly nameField = form(this.nameSignal, (f) => {
    validate(f, (ctx) => (!ctx.value() ? [{ kind: "required" }] : []));
    validate(f, (ctx) => (ctx.value() === this.data ? [{ kind: "notChanged" }] : []));
    // The unchanged original name is reported as "notChanged" only.
    validate(f, (ctx) =>
      ctx.value() !== this.data && this.policyService.isPolicyNameTaken(ctx.value()) ? [{ kind: "nameTaken" }] : []
    );
  });

  readonly isInvalid = computed(() => this.nameField().errors().length > 0);
  // Set once the name has differed from the original, so that an error is shown from then on even when the
  // user types the original name back.
  private edited = false;

  readonly actions = computed<DialogAction<"submit" | null>[]>(() => [
    {
      label: $localize`:@@policy.copyPolicy:Copy Policy`,
      value: "submit",
      type: "confirm",
      disabled: this.isInvalid()
    }
  ]);

  constructor() {
    super();
    // Copy is disabled for an invalid name, so the reason shows while the field still has focus.
    effect(() => {
      if (this.nameSignal() !== this.data) {
        this.edited = true;
      }
      if (this.edited && this.isInvalid()) {
        this.nameField().markAsTouched();
      }
    });
  }

  onAction(value: "submit" | null): void {
    if (value === "submit" && !this.isInvalid()) {
      this.close(this.nameSignal());
    } else {
      this.close(null);
    }
  }
}
