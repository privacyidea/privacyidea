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

import { Component, computed, ElementRef, inject, input, linkedSignal, output, viewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { TokenEnrollmentData, TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { getTokenApiPayloadMapper } from "@app/mappers/token-api-payload/token-api-payload-mapper-registry";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { tokenTypes } from "@utils/token.utils";

@Component({
  selector: "app-template-added-token-row",
  standalone: true,
  imports: [MatIconModule, MatButtonModule, MatCheckboxModule, MatExpansionModule, EnrollTokenTypeSwitchComponent],
  templateUrl: "./template-added-token-row.component.html",
  styleUrls: ["./template-added-token-row.component.scss"]
})
export class TemplateAddedTokenRowComponent {
  readonly tokenEnrollmentPayload = input.required<TokenEnrollmentPayload>();
  readonly index = input.required<number>();
  readonly onRemoveToken = output<number>();

  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);
  private readonly expansionPanel = viewChild(MatExpansionPanel);
  private readonly elementRef = inject(ElementRef);

  readonly userAssign = linkedSignal(() => this.tokenEnrollmentPayload().user === true);

  readonly tokenTypeDescription = computed(() => {
    const type = this.tokenEnrollmentPayload().type;
    return tokenTypes.find((t) => t.key === type)?.text ?? "";
  });

  readonly tokenEnrollmentData = linkedSignal<TokenEnrollmentPayload, Partial<TokenEnrollmentData> | null>({
    source: this.tokenEnrollmentPayload,
    computation: (payload) => {
      const mapper = getTokenApiPayloadMapper(payload?.type);
      if (!mapper) return null;
      return mapper.fromApiPayload(payload);
    }
  });

  // Pulled by the parent at save time.
  getCurrentPayload(): TokenEnrollmentPayload | null {
    const payload = this.tokenEnrollmentPayload();
    const strategy = this.enrollSwitch()?.currentStrategy();
    const data = this.tokenEnrollmentData();

    if (!strategy || !data) {
      return { ...payload, user: this.userAssign() };
    }
    const args = strategy.buildEnrollmentArgs({ type: payload.type, ...data });
    if (!args) return null;
    return { ...args.mapper.toApiPayload(args.data), user: this.userAssign() };
  }

  // Called by the parent body when a save attempt fails:
  scrollIntoView(): void {
    this.expansionPanel()?.open();
    this.elementRef.nativeElement.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  toggleUserAssign(checked: boolean) {
    this.userAssign.set(checked);
  }

  removeToken() {
    if (this.index() >= 0) {
      this.onRemoveToken.emit(this.index());
    }
  }
}
