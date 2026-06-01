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

import { Component, computed, model } from "@angular/core";
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

  protected onEditToken(patch: Partial<TokenEnrollmentPayload>, index: number) {
    const updatedTokens = this.tokens().map((token, i) => {
      if (i !== index) return token;
      const updatedToken = { ...token, ...patch };
      Object.keys(updatedToken).forEach((key) => {
        if (updatedToken[key] === undefined) {
          delete updatedToken[key];
        }
      });
      return updatedToken;
    });
    this._updateTokens(updatedTokens);
  }

  protected onDeleteToken(index: number) {
    this._updateTokens(this.tokens().filter((_, i) => i !== index));
  }

  protected onAddToken(tokenType: string) {
    const updatedTokens = [...this.tokens(), { type: tokenType as TokenTypeKey }];
    this._updateTokens(updatedTokens);
  }

  private _updateTokens(tokens: TokenEnrollmentPayload[]) {
    const editedTemplate: ContainerTemplate = {
      ...this.template(),
      template_options: {
        ...this.template().template_options,
        tokens
      }
    };
    this.template.set(editedTemplate);
  }

  protected _toTitleCase(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}
