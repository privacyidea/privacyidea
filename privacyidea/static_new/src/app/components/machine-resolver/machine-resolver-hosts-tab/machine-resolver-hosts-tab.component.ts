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

import { Component, input, linkedSignal, output, ViewEncapsulation } from "@angular/core";
import {
  HostsMachineResolverData,
  MachineResolverData
} from "../../../services/machine-resolver/machine-resolver.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-machine-resolver-hosts-tab",
  templateUrl: "./machine-resolver-hosts-tab.component.html",
  styleUrls: ["./machine-resolver-hosts-tab.component.scss"],
  imports: [MatFormFieldModule, MatInputModule, FormsModule],
  standalone: true,
  encapsulation: ViewEncapsulation.ShadowDom
})
export class MachineResolverHostsTabComponent {
  readonly isEditMode = input.required<boolean>();
  readonly machineResolverData = input.required<MachineResolverData>();
  readonly hostsData = linkedSignal<HostsMachineResolverData>(
    () => this.machineResolverData() as HostsMachineResolverData
  );
  readonly onNewData = output<MachineResolverData>();
  readonly onNewValidator = output<(data: MachineResolverData) => boolean>();

  ngOnInit(): void {
    this.onNewValidator.emit(this.isValid.bind(this));
  }

  updateData(
    args:
      | { patch: Partial<HostsMachineResolverData>; remove?: (keyof HostsMachineResolverData)[] }
      | { patch?: Partial<HostsMachineResolverData>; remove: (keyof HostsMachineResolverData)[] }
      | Partial<HostsMachineResolverData>
  ) {
    let patch: Partial<HostsMachineResolverData> = {};
    let remove: (keyof HostsMachineResolverData)[] = [];
    if ("remove" in args || "patch" in args) {
      const complexArgs = args as {
        patch?: Partial<HostsMachineResolverData>;
        remove?: (keyof HostsMachineResolverData)[];
      };
      patch = complexArgs.patch || {};
      remove = complexArgs.remove || [];
    } else {
      patch = args as Partial<HostsMachineResolverData>;
    }
    const newData = { ...this.machineResolverData(), ...patch, type: "hosts" };
    if (remove.length > 0) {
      remove.forEach((key) => {
        delete newData[key];
      });
    }
    this.onNewData.emit(newData);
  }

  isValid(data: MachineResolverData): boolean {
    if (data.type !== "hosts") return false;
    if ((data as HostsMachineResolverData).filename?.trim() === "") return false;
    return true;
  }
}
