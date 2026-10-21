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
import { FormField } from "@angular/forms/signals";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import {
  panelCompleteness,
  TIQR_KEYS,
  TokenTypeConfigForm
} from "@components/configuration/token-type-config/token-type-config.form";
import { PanelIncompleteComponent } from "@components/configuration/token-type-config/token-types/panel-incomplete/panel-incomplete.component";
import {
  TIQR_AUTH_SERVER,
  TIQR_INFO_URL,
  TIQR_LOGO_URL,
  TIQR_OCRASUITE,
  TIQR_REG_SERVER,
  TIQR_SERVICE_DISPLAYNAME,
  TIQR_SERVICE_IDENTIFIER
} from "@constants/token.constants";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

@Component({
  selector: "app-tiqr-config",
  standalone: true,
  imports: [MatExpansionModule, MatFormFieldModule, MatInputModule, FormField, PanelIncompleteComponent],
  templateUrl: "./tiqr-config.component.html"
})
export class TiqrConfigComponent {
  protected readonly TIQR_REG_SERVER = TIQR_REG_SERVER;
  protected readonly TIQR_AUTH_SERVER = TIQR_AUTH_SERVER;
  protected readonly TIQR_SERVICE_DISPLAYNAME = TIQR_SERVICE_DISPLAYNAME;
  protected readonly TIQR_SERVICE_IDENTIFIER = TIQR_SERVICE_IDENTIFIER;
  protected readonly TIQR_LOGO_URL = TIQR_LOGO_URL;
  protected readonly TIQR_INFO_URL = TIQR_INFO_URL;
  protected readonly TIQR_OCRASUITE = TIQR_OCRASUITE;
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  config = input.required<TokenTypeConfigForm>();
  protected readonly panel = panelCompleteness(this.config, () => TIQR_KEYS);
}
