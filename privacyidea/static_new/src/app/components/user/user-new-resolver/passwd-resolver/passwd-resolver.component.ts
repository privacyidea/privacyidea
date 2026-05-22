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
import { Component, effect, input, signal } from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { PasswdResolverData } from "@services/resolver/resolver.service";

interface PasswdFormModel {
  fileName: string;
}

@Component({
  selector: "app-passwd-resolver",
  standalone: true,
  imports: [FormField, MatFormField, MatLabel, MatInput, MatError, ClearableInputComponent],
  templateUrl: "./passwd-resolver.component.html",
  styleUrl: "./passwd-resolver.component.scss"
})
export class PasswdResolverComponent {
  data = input<Partial<PasswdResolverData>>({});

  model = signal<PasswdFormModel>({ fileName: "" });

  passwdForm = form(this.model, (f) => {
    required(f.fileName);
  });

  isValid = () => this.passwdForm().valid();
  isDirty = () => this.passwdForm().dirty();
  getValue = () => this.model();

  constructor() {
    effect(() => {
      const initial = this.data()?.fileName || this.data()?.filename;
      if (initial !== undefined) {
        this.model.set({ fileName: initial });
        this.passwdForm().reset();
      }
    });
  }
}
