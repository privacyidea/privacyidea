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

import { Component, inject } from "@angular/core";
import { MachineresolverPanelNewComponent } from "./machineresolver-panel-new/machineresolver-panel-new.component";
import { MachineresolverPanelEditComponent } from "./machineresolver-panel-edit/machineresolver-panel-edit.component";
import { MatExpansionModule } from "@angular/material/expansion";
import {
  MachineresolverService,
  MachineresolverServiceInterface
} from "../../services/machineresolver/machineresolver.service";

@Component({
  selector: "app-machineresolver",
  templateUrl: "./machineresolver.component.html",
  styleUrls: ["./machineresolver.component.scss"],
  imports: [MachineresolverPanelNewComponent, MachineresolverPanelEditComponent, MatExpansionModule]
})
export class MachineresolverComponent {
  machineresolverService: MachineresolverServiceInterface = inject(MachineresolverService);
}
