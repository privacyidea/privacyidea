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
import { Component, computed, effect, inject, input, signal } from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatHint, MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ResolverService, SQLResolverData } from "@services/resolver/resolver.service";
import { parseBooleanValue } from "@utils/parse-boolean-value";

interface SqlPreset {
  name: string;
  table: string;
  map: string;
}

interface SqlFormModel {
  Driver: string;
  Server: string;
  Table: string;
  Limit: string;
  Map: string;
  Database: string;
  Port: string;
  User: string;
  Password: string;
  Password_Hash_Type: string;
  poolSize: string;
  poolTimeout: string;
  poolRecycle: string;
  Editable: boolean;
  conParams: string;
  Encoding: string;
  Where: string;
}

@Component({
  selector: "app-sql-resolver",
  standalone: true,
  imports: [
    FormField,
    MatFormField,
    MatLabel,
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
      map: '{ "userid" : "ID", "username": "user_login", "email" : "user_email", "givenname" : "display_name", "password" : "user_pass" }'
    },
    {
      name: "OTRS",
      table: "users",
      map: '{ "userid" : "id", "username": "login", "givenname" : "first_name", "surname" : "last_name", "password" : "pw" }'
    },
    {
      name: "TINE 2.0",
      table: "tine20_accounts",
      map: '{ "userid" : "id", "username": "login_name", "email" : "email", "givenname" : "first_name", "surname" : "last_name", "password" : "password" }'
    },
    {
      name: "Owncloud",
      table: "oc_users",
      map: '{ "userid" : "uid", "username": "uid", "givenname" : "displayname", "password" : "password" }'
    },
    {
      name: "Typo3",
      table: "be_users",
      map: '{ "userid" : "uid", "username": "username", "givenname" : "realName", "password" : "password", "email": "email" }'
    },
    {
      name: "Drupal",
      table: "user",
      map: '{"userid": "uid", "username": "name", "email": "mail", "password": "pass" }'
    }
  ];

  model = signal<SqlFormModel>({
    Driver: "",
    Server: "",
    Table: "",
    Limit: "",
    Map: "",
    Database: "",
    Port: "",
    User: "",
    Password: "",
    Password_Hash_Type: "",
    poolSize: "5",
    poolTimeout: "10",
    poolRecycle: "7200",
    Editable: false,
    conParams: "",
    Encoding: "",
    Where: ""
  });

  sqlForm = form(this.model, (f) => {
    required(f.Driver);
    required(f.Server);
    required(f.Table);
    required(f.Limit);
    required(f.Map);
  });

  isValid = () => this.sqlForm().valid();
  isDirty = () => this.sqlForm().dirty();
  getValue = () => this.model();

  applySqlPreset(preset: SqlPreset): void {
    this.model.update(m => ({
      ...m,
      Table: preset.table,
      Map: preset.map,
      poolSize: "5",
      poolTimeout: "10",
      poolRecycle: "7200"
    }));
  }

  constructor() {
    effect(() => {
      const initial = this.data();
      this.model.update(m => ({
        ...m,
        ...(initial.Driver !== undefined ? { Driver: initial.Driver } : {}),
        ...(initial.Server !== undefined ? { Server: initial.Server } : {}),
        ...(initial.Table !== undefined ? { Table: initial.Table } : {}),
        ...(initial.Limit !== undefined ? { Limit: String(initial.Limit) } : {}),
        ...(initial.Map !== undefined ? { Map: initial.Map } : {}),
        ...(initial.Database !== undefined ? { Database: initial.Database } : {}),
        ...(initial.Port !== undefined ? { Port: String(initial.Port) } : {}),
        ...(initial.User !== undefined ? { User: initial.User } : {}),
        ...(initial.Password !== undefined ? { Password: initial.Password } : {}),
        ...(initial.Password_Hash_Type !== undefined ? { Password_Hash_Type: initial.Password_Hash_Type } : {}),
        ...(initial.poolSize !== undefined ? { poolSize: String(initial.poolSize) } : {}),
        ...(initial.poolTimeout !== undefined ? { poolTimeout: String(initial.poolTimeout) } : {}),
        ...(initial.poolRecycle !== undefined ? { poolRecycle: String(initial.poolRecycle) } : {}),
        ...(initial.Editable !== undefined ? { Editable: parseBooleanValue(initial.Editable) } : {}),
        ...(initial.conParams !== undefined ? { conParams: initial.conParams } : {}),
        ...(initial.Encoding !== undefined ? { Encoding: initial.Encoding } : {}),
        ...(initial.Where !== undefined ? { Where: initial.Where } : {})
      }));
      this.sqlForm().reset();
    });
  }
}
