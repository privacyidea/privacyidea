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
import { SCIMResolverData } from "@services/resolver/resolver.service";

interface ScimFormModel {
  Authserver: string;
  Resourceserver: string;
  Client: string;
  Secret: string;
  Mapping: string;
}

@Component({
  selector: "app-scim-resolver",
  standalone: true,
  imports: [FormField, MatFormField, MatLabel, MatInput, MatError, ClearableInputComponent],
  templateUrl: "./scim-resolver.component.html",
  styleUrl: "./scim-resolver.component.scss"
})
export class ScimResolverComponent {
  data = input<Partial<SCIMResolverData>>({});

  model = signal<ScimFormModel>({
    Authserver: "",
    Resourceserver: "",
    Client: "",
    Secret: "",
    Mapping: ""
  });

  scimForm = form(this.model, (f) => {
    required(f.Authserver);
    required(f.Resourceserver);
    required(f.Client);
    required(f.Secret);
    required(f.Mapping);
  });

  isValid = () => this.scimForm().valid();
  isDirty = () => this.scimForm().dirty();
  getValue = () => this.model();

  constructor() {
    effect(() => {
      const initial = this.data();
      this.model.set({
        Authserver: initial.Authserver ?? "",
        Resourceserver: initial.Resourceserver ?? "",
        Client: initial.Client ?? "",
        Secret: initial.Secret ?? "",
        Mapping: initial.Mapping ?? ""
      });
      this.scimForm().reset();
    });
  }
}
