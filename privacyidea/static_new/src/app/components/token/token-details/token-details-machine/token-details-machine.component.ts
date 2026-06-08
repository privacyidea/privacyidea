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
import { Component, computed, inject } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import {
  MachineService,
  MachineServiceInterface,
  TokenApplication,
  TokenApplications
} from "@services/machine/machine.service";

@Component({
  selector: "app-token-details-machine",
  standalone: true,
  imports: [MatIconButton, MatIcon],
  templateUrl: "./token-details-machine.component.html",
  styleUrl: "./token-details-machine.component.scss"
})
export class TokenDetailsMachineComponent {
  private static readonly hiddenKeys = new Set(["serial", "application", "type", "id"]);

  private machineService: MachineServiceInterface = inject(MachineService);
  private contentService: ContentServiceInterface = inject(ContentService);

  machineData = computed<TokenApplications>(() => this.machineService.tokenApplications() || []);

  visibleEntries(machine: TokenApplication): [string, string][] {
    const out: [string, string][] = [];
    for (const [key, value] of Object.entries(machine)) {
      if (TokenDetailsMachineComponent.hiddenKeys.has(key)) continue;
      if (key === "options" && value && typeof value === "object") {
        for (const [optKey, optValue] of Object.entries(value as Record<string, string>)) {
          if (optValue !== null && optValue !== undefined && optValue !== "") {
            out.push([optKey, String(optValue)]);
          }
        }
      } else if (value !== null && value !== undefined && value !== "") {
        out.push([key, String(value)]);
      }
    }
    return out;
  }

  unassignMachine(mtid: number, application: string): void {
    this.machineService
      .deleteAssignMachineToToken({
        serial: this.contentService.tokenSerial(),
        application: application,
        mtid: mtid.toString()
      })
      .subscribe({
        next: () => {
          this.machineService.tokenApplicationResource.reload();
        }
      });
  }
}
