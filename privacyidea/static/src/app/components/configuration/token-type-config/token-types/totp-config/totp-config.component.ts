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
import { Component, computed, input } from "@angular/core";
import { FieldTree, FormField } from "@angular/forms/signals";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  panelCompleteness,
  TOTP_KEYS,
  TokenTypeConfigForm
} from "@components/configuration/token-type-config/token-type-config.form";
import { PanelIncompleteComponent } from "@components/configuration/token-type-config/token-types/panel-incomplete/panel-incomplete.component";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { TOTP_HASHLIB, TOTP_TIME_SHIFT, TOTP_TIME_STEP, TOTP_TIME_WINDOW } from "@constants/token.constants";
import { ERR } from "@utils/form-rules.utils";
import { clearField, hasError } from "@utils/form-state.utils";
import { labeledOptions } from "@utils/value-label.utils";

@Component({
  selector: "app-totp-config",
  standalone: true,
  imports: [
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ClearButtonComponent,
    FormField,
    PanelIncompleteComponent
  ],
  templateUrl: "./totp-config.component.html"
})
export class TotpConfigComponent {
  protected readonly TOTP_TIME_STEP = TOTP_TIME_STEP;
  protected readonly TOTP_TIME_WINDOW = TOTP_TIME_WINDOW;
  protected readonly TOTP_TIME_SHIFT = TOTP_TIME_SHIFT;
  protected readonly TOTP_HASHLIB = TOTP_HASHLIB;
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  config = input.required<TokenTypeConfigForm>();
  protected readonly panel = panelCompleteness(this.config, () => TOTP_KEYS);
  totpSteps = input.required<string[]>();
  hashLibs = input.required<string[]>();
  readonly hashLibOptions = computed(() => labeledOptions(this.hashLibs(), { vocabulary: true }));

  clearValue(field: FieldTree<string>): void {
    clearField(field, "");
  }
}
