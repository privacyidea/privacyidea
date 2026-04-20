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
import { MatSelectModule } from "@angular/material/select";
import { MachineService, MachineServiceInterface } from "../../../services/machine/machine.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { TokenApplicationsOfflineComponent } from "./token-applications-offline/token-applications-offline.component";
import { TokenApplicationsSshComponent } from "./token-applications-ssh/token-applications-ssh.component";

@Component({
  selector: "app-token-applications",
  standalone: true,
  imports: [
    TokenApplicationsSshComponent,
    TokenApplicationsOfflineComponent,
    MatSelectModule,
    ScrollToTopDirective
  ],
  templateUrl: "./token-applications.component.html",
  styleUrls: ["./token-applications.component.scss"]
})
export class TokenApplicationsComponent {
  private readonly machineService: MachineServiceInterface =
    inject(MachineService);

  selectedApplicationType = this.machineService.selectedApplicationType;
}
