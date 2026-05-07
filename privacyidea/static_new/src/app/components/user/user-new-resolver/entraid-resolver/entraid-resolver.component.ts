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

import { Component, signal } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { MatCheckbox } from "@angular/material/checkbox";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatDivider } from "@angular/material/list";
import { MatError, MatOption, MatSelect } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { HttpConfigComponent } from "@components/user/user-new-resolver/http-resolver/http-config/http-config.component";
import { HttpGroupsAttributeComponent } from "@components/user/user-new-resolver/http-resolver/http-groups-attribute/http-groups-attribute.component";
import {
  AttributeMappingRow,
  HttpResolverComponent
} from "@components/user/user-new-resolver/http-resolver/http-resolver.component";

@Component({
  selector: "app-entraid-resolver",
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatHint,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatDivider,
    MatError,
    ReactiveFormsModule,
    MatDivider,
    MatButtonToggleGroup,
    MatButtonToggle,
    HttpConfigComponent,
    ClearableInputComponent,
    HttpGroupsAttributeComponent
  ],
  templateUrl: "../http-resolver/http-resolver.component.html",
  styleUrl: "../http-resolver//http-resolver.component.scss"
})
export class EntraidResolverComponent extends HttpResolverComponent {
  override isAdvanced: boolean = true;
  override isAuthorizationExpanded: boolean = true;
  override defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "id" },
    { privacyideaAttr: "username", userStoreAttr: "userPrincipalName" },
    { privacyideaAttr: "email", userStoreAttr: "mail" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenName" },
    { privacyideaAttr: "mobile", userStoreAttr: "mobilePhone" },
    { privacyideaAttr: "phone", userStoreAttr: "businessPhones" },
    { privacyideaAttr: "surname", userStoreAttr: "surname" }
  ]);

  constructor() {
    super();
  }
}
