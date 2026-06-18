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

import { Component, computed, model, viewChildren } from "@angular/core";
import { MatChipsModule } from "@angular/material/chips";
import { MatIcon } from "@angular/material/icon";
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { TemplateAddedTokenRowComponent } from "@components/container/container-templates/container-template-edit-page/template-added-token-row/template-added-token-row.component";
import { ContainerTemplate } from "@services/container/container.service";
import { TokenTypeKey } from "@services/token/token.service";

@Component({
  selector: "app-container-template-edit-body",
  standalone: true,
  imports: [TemplateAddedTokenRowComponent, MatChipsModule, MatIcon],
  templateUrl: "./container-template-edit-body.component.html",
  styleUrl: "./container-template-edit-body.component.scss"
})
export class ContainerTemplateEditBodyComponent {
  readonly template = model.required<ContainerTemplate>();
  readonly availableTokenTypes = model.required<string[]>();

  protected readonly tokens = computed(() => this.template().template_options?.tokens || []);
  protected readonly tokenRows = viewChildren(TemplateAddedTokenRowComponent);

  // Pull each row's current payload at save time.
  private _firstInvalidRow: TemplateAddedTokenRowComponent | null = null;
  collectTokens(): TokenEnrollmentPayload[] | null {
    this._firstInvalidRow = null;
    const payloads: TokenEnrollmentPayload[] = [];
    let hasInvalid = false;
    for (const row of this.tokenRows()) {
      const payload = row.getCurrentPayload();
      if (payload === null) {
        hasInvalid = true;
        if (!this._firstInvalidRow) this._firstInvalidRow = row;
      } else if (!hasInvalid) {
        payloads.push(payload);
      }
    }
    return hasInvalid ? null : payloads;
  }

  scrollToFirstInvalid(): void {
    this._firstInvalidRow?.scrollIntoView();
  }

  protected onDeleteToken(index: number) {
    this._updateTokens(this.tokens().filter((_, i) => i !== index));
  }

  protected onAddToken(tokenType: string) {
    this._updateTokens([...this.tokens(), { type: tokenType as TokenTypeKey }]);
  }

  private _updateTokens(tokens: TokenEnrollmentPayload[]) {
    this.template.set({
      ...this.template(),
      template_options: {
        ...this.template().template_options,
        tokens
      }
    });
  }

  protected _toTitleCase(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}
