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
import { DOCUMENT } from "@angular/common";
import { MatSelectModule } from "@angular/material/select";
import { MachineService, MachineServiceInterface } from "../../../services/machine/machine.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { TokenApplicationsOfflineComponent } from "./token-applications-offline/token-applications-offline.component";
import { TokenApplicationsSshComponent } from "./token-applications-ssh/token-applications-ssh.component";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";

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
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly document: Document = inject(DOCUMENT);

  selectedApplicationType = this.machineService.selectedApplicationType;

  // Centralized toggleFilter for SSH and Offline application tables
  toggleFilter(filterKeyword: string): void {
    let newValue;
    if (filterKeyword === "machineid & resolver") {
      const current = this.machineService.machineFilter();
      const hasMachineId = current.hasKey("machineid");
      const hasResolver = current.hasKey("resolver");

      if (hasMachineId && hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: newValue });
      } else if (!hasMachineId && !hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: newValue });
      } else if (hasMachineId && !hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: current });
      } else {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
      }
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.machineService.machineFilter()
      });
    }
    this.machineService.machineFilter.set(newValue);
  }

  // Centralized icon state for SSH and Offline application tables
  getFilterIconName(keyword: string): string {
    if (keyword === "machineid & resolver") {
      const current = this.machineService.machineFilter();
      const selected = current.hasKey("machineid") && current.hasKey("resolver");
      return selected ? "filter_alt_off" : "filter_alt";
    }
    const isSelected = this.machineService.machineFilter().hasKey(keyword);
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  // Centralized click handlers that also refocus the correct input field
  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.focusActiveInput();
  }

  onAdvancedFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.focusActiveInput();
  }

  private focusActiveInput(): void {
    // Determine which input to focus based on the selected application type
    const type = this.selectedApplicationType();
    const id = type === "ssh" ? "ssh-filter-input" : "offline-filter-input";
    setTimeout(() => {
      const el = this.document.getElementById(id) as HTMLInputElement | null;
      el?.focus();
    });
  }
}
