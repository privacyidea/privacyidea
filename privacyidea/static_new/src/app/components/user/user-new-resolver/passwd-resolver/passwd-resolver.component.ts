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
import { Component, computed, effect, input } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { PasswdResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: "app-passwd-resolver",
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule, MatFormField, MatLabel, MatInput, MatError],
  templateUrl: "./passwd-resolver.component.html",
  styleUrl: "./passwd-resolver.component.scss"
})
export class PasswdResolverComponent {
  data = input<Partial<PasswdResolverData>>({});

  filenameControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });

  controls = computed(() => ({
    fileName: this.filenameControl
  }));

  constructor() {
    effect(() => {
      const initial = this.data()?.fileName;
      if (initial !== undefined) {
        this.filenameControl.setValue(initial, { emitEvent: false });
      }
    });
  }
}
