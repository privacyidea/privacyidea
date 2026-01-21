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
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { SCIMResolverData } from "../../../../services/resolver/resolver.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-scim-resolver",
  standalone: true,
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    ReactiveFormsModule,
    MatInput,
    MatError,
    ClearableInputComponent
  ],
  templateUrl: "./scim-resolver.component.html",
  styleUrl: "./scim-resolver.component.scss"
})
export class ScimResolverComponent {
  data = input<Partial<SCIMResolverData>>({});

  authServerControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  resourceServerControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  clientControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  secretControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  mappingControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });

  controls = computed<Record<string, AbstractControl>>(() => ({
    Authserver: this.authServerControl,
    Resourceserver: this.resourceServerControl,
    Client: this.clientControl,
    Secret: this.secretControl,
    Mapping: this.mappingControl
  }));

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.Authserver !== undefined) {
        this.authServerControl.setValue(initial.Authserver, { emitEvent: false });
      }
      if (initial.Resourceserver !== undefined) {
        this.resourceServerControl.setValue(initial.Resourceserver, { emitEvent: false });
      }
      if (initial.Client !== undefined) {
        this.clientControl.setValue(initial.Client, { emitEvent: false });
      }
      if (initial.Secret !== undefined) {
        this.secretControl.setValue(initial.Secret, { emitEvent: false });
      }
      if (initial.Mapping !== undefined) {
        this.mappingControl.setValue(initial.Mapping, { emitEvent: false });
      }
    });
  }
}
