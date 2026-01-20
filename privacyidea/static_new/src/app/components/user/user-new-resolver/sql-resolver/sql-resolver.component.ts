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
import { Component, computed, effect, inject, input } from "@angular/core";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatHint, MatInput } from "@angular/material/input";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { ResolverService, SQLResolverData } from "../../../../services/resolver/resolver.service";
import { MatOption, MatSelect } from "@angular/material/select";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-sql-resolver",
  standalone: true,
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    ReactiveFormsModule,
    MatInput,
    MatCheckbox,
    MatHint,
    MatError,
    MatButtonModule,
    MatSelect,
    MatOption,
    ClearableInputComponent
  ],
  templateUrl: "./sql-resolver.component.html",
  styleUrl: "./sql-resolver.component.scss"
})
export class SqlResolverComponent {
  private readonly resolverService = inject(ResolverService);

  data = input<Partial<SQLResolverData>>({});

  isEditMode = computed(() => !!this.resolverService.selectedResolverName());

  readonly sqlPresets = [
    {
      name: "Wordpress",
      table: "wp_users",
      map: "{ \"userid\" : \"ID\", \"username\": \"user_login\", \"email\" : \"user_email\", \"givenname\" : \"display_name\", \"password\" : \"user_pass\" }"
    },
    {
      name: "OTRS",
      table: "users",
      map: "{ \"userid\" : \"id\", \"username\": \"login\", \"givenname\" : \"first_name\", \"surname\" : \"last_name\", \"password\" : \"pw\" }"
    },
    {
      name: "TINE 2.0",
      table: "tine20_accounts",
      map: "{ \"userid\" : \"id\", \"username\": \"login_name\", \"email\" : \"email\", \"givenname\" : \"first_name\", \"surname\" : \"last_name\", \"password\" : \"password\" }"
    },
    {
      name: "Owncloud",
      table: "oc_users",
      map: "{ \"userid\" : \"uid\", \"username\": \"uid\", \"givenname\" : \"displayname\", \"password\" : \"password\" }"
    },
    {
      name: "Typo3",
      table: "be_users",
      map: "{ \"userid\" : \"uid\", \"username\": \"username\", \"givenname\" : \"realName\", \"password\" : \"password\", \"email\": \"email\" }"
    },
    {
      name: "Drupal",
      table: "user",
      map: "{\"userid\": \"uid\", \"username\": \"name\", \"email\": \"mail\", \"password\": \"pass\" }"
    }
  ];

  driverControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  serverControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  tableControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  limitControl = new FormControl<number | undefined>(undefined, { validators: [Validators.required] });
  mapControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });

  databaseControl = new FormControl<string>("", { nonNullable: true });
  portControl = new FormControl<number | undefined>(undefined);
  userControl = new FormControl<string>("", { nonNullable: true });
  passwordControl = new FormControl<string>("", { nonNullable: true });
  passwordHashTypeControl = new FormControl<string>("", { nonNullable: true });
  poolSizeControl = new FormControl<number>(5, { nonNullable: true });
  poolTimeoutControl = new FormControl<number>(10, { nonNullable: true });
  poolRecycleControl = new FormControl<number>(7200, { nonNullable: true });
  editableControl = new FormControl<boolean>(false, { nonNullable: true });
  conParamsControl = new FormControl<string>("", { nonNullable: true });
  encodingControl = new FormControl<string>("", { nonNullable: true });
  whereControl = new FormControl<string>("", { nonNullable: true });

  controls = computed<Record<string, AbstractControl>>(() => ({
    Driver: this.driverControl,
    Server: this.serverControl,
    Table: this.tableControl,
    Limit: this.limitControl,
    Map: this.mapControl,
    Database: this.databaseControl,
    Port: this.portControl,
    User: this.userControl,
    Password: this.passwordControl,
    Password_Hash_Type: this.passwordHashTypeControl,
    poolSize: this.poolSizeControl,
    poolTimeout: this.poolTimeoutControl,
    poolRecycle: this.poolRecycleControl,
    Editable: this.editableControl,
    conParams: this.conParamsControl,
    Encoding: this.encodingControl,
    Where: this.whereControl
  }));

  applySqlPreset(preset: any): void {
    this.tableControl.setValue(preset.table);
    this.mapControl.setValue(preset.map);
    this.poolSizeControl.setValue(5);
    this.poolTimeoutControl.setValue(10);
    this.poolRecycleControl.setValue(7200);
  }

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.Driver !== undefined) this.driverControl.setValue(initial.Driver, { emitEvent: false });
      if (initial.Server !== undefined) this.serverControl.setValue(initial.Server, { emitEvent: false });
      if (initial.Table !== undefined) this.tableControl.setValue(initial.Table, { emitEvent: false });
      if (initial.Limit !== undefined) this.limitControl.setValue(initial.Limit, { emitEvent: false });
      if (initial.Map !== undefined) this.mapControl.setValue(initial.Map, { emitEvent: false });

      if (initial.Database !== undefined) this.databaseControl.setValue(initial.Database, { emitEvent: false });
      if (initial.Port !== undefined) this.portControl.setValue(initial.Port, { emitEvent: false });
      if (initial.User !== undefined) this.userControl.setValue(initial.User, { emitEvent: false });
      if (initial.Password !== undefined) this.passwordControl.setValue(initial.Password, { emitEvent: false });
      if (initial.Password_Hash_Type !== undefined) this.passwordHashTypeControl.setValue(initial.Password_Hash_Type, { emitEvent: false });
      if (initial.poolSize !== undefined) this.poolSizeControl.setValue(initial.poolSize, { emitEvent: false });
      if (initial.poolTimeout !== undefined) this.poolTimeoutControl.setValue(initial.poolTimeout, { emitEvent: false });
      if (initial.poolRecycle !== undefined) this.poolRecycleControl.setValue(initial.poolRecycle, { emitEvent: false });
      if (initial.Editable !== undefined) this.editableControl.setValue(initial.Editable, { emitEvent: false });
      if (initial.conParams !== undefined) this.conParamsControl.setValue(initial.conParams, { emitEvent: false });
      if (initial.Encoding !== undefined) this.encodingControl.setValue(initial.Encoding, { emitEvent: false });
      if (initial.Where !== undefined) this.whereControl.setValue(initial.Where, { emitEvent: false });
    });
  }
}
