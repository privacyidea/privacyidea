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
import { NgClass } from "@angular/common";
import { Component, computed, inject, input, Input, linkedSignal, signal, Signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatList, MatListItem } from "@angular/material/list";
import { MatCell, MatColumnDef, MatRow, MatTableModule } from "@angular/material/table";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import {
  MachineService,
  MachineServiceInterface,
  TokenApplication,
  TokenApplications
} from "../../../../services/machine/machine.service";
import { CdkTableDataSourceInput } from "@angular/cdk/table";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

@Component({
  selector: "app-token-details-machine",
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatList,
    MatListItem,
    FormsModule,
    MatIconButton,
    MatIcon,
    MatDivider,
    MatRow,
    NgClass
  ],
  templateUrl: "./token-details-machine.component.html",
  styleUrl: "./token-details-machine.component.scss"
})
export class TokenDetailsMachineComponent {
  protected readonly JSON = JSON;
  protected readonly Object = Object;
  private machineService: MachineServiceInterface = inject(MachineService);
  private contentService: ContentServiceInterface = inject(ContentService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);

  machineData = computed<TokenApplications>(() => this.machineService.tokenApplications() || []);

  unassignMachine(mtid: number, application: "ssh" | "offline"): void {
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

  dataSourceFromMachine(machine: TokenApplication): CdkTableDataSourceInput<any> {
    return new Array(machine);
  }
}
