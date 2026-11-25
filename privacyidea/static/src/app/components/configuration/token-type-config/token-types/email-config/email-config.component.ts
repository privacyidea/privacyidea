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
import { Component, input } from "@angular/core";
import { FieldTree, FormField } from "@angular/forms/signals";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import {
  panelCompleteness,
  EMAIL_KEYS,
  TokenTypeConfigForm
} from "@components/configuration/token-type-config/token-type-config.form";
import { PanelIncompleteComponent } from "@components/configuration/token-type-config/token-types/panel-incomplete/panel-incomplete.component";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { EMAIL_SMTP_SERVER_KEY, EMAIL_VALIDITY_TIME_KEY } from "@constants/token.constants";
import { ERR } from "@utils/form-rules.utils";
import { clearField, hasError } from "@utils/form-state.utils";

@Component({
  selector: "app-email-config",
  standalone: true,
  imports: [
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    RouterLink,
    ClearButtonComponent,
    FormField,
    PanelIncompleteComponent
  ],
  templateUrl: "./email-config.component.html"
})
export class EmailConfigComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;
  config = input.required<TokenTypeConfigForm>();
  protected readonly panel = panelCompleteness(this.config, () => EMAIL_KEYS);
  smtpServers = input.required<string[]>();
  smtpServersListable = input.required<boolean>();
  expanded = input<boolean>(false);

  clearValue(field: FieldTree<string>): void {
    clearField(field, "");
  }

  protected readonly EMAIL_SMTP_SERVER_KEY = EMAIL_SMTP_SERVER_KEY;
  protected readonly EMAIL_VALIDITY_TIME_KEY = EMAIL_VALIDITY_TIME_KEY;
}
