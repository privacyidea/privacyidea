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

import { Component, inject, OnDestroy } from "@angular/core";
import { MatExpansionModule } from "@angular/material/expansion";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  MachineResolverService,
  MachineResolverServiceInterface
} from "@services/machine-resolver/machine-resolver.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MachineResolverPanelEditComponent } from "./machine-resolver-panel-edit/machine-resolver-panel-edit.component";
import { MachineResolverPanelNewComponent } from "./machine-resolver-panel-new/machine-resolver-panel-new.component";

@Component({
  selector: "app-machine-resolver",
  templateUrl: "./machine-resolver.component.html",
  styleUrls: ["./machine-resolver.component.scss"],
  imports: [MachineResolverPanelNewComponent, MachineResolverPanelEditComponent, MatExpansionModule]
})
export class MachineResolverComponent implements OnDestroy {
  machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  authService: AuthServiceInterface = inject(AuthService);
  private readonly pendingChangesService = inject(PendingChangesService);

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }
}
