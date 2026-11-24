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

import { Component, effect, input, linkedSignal, output, untracked } from "@angular/core";
import { disabled, form, FormField } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { HostsMachineResolverData, MachineResolverData } from "@services/machine-resolver/machine-resolver.service";
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import { hasError, touchAll } from "@utils/form-state.utils";

interface HostsFormModel {
  filename: string;
}

function toFormModel(data: MachineResolverData): HostsFormModel {
  return { filename: (data as HostsMachineResolverData).filename ?? "" };
}

// A filename the data did not hold and the user left empty stays absent from the emitted data.
function toData(model: HostsFormModel, base: MachineResolverData): HostsMachineResolverData {
  const data: HostsMachineResolverData = { ...(base as HostsMachineResolverData), type: "hosts" };
  if (model.filename !== "" || data.filename !== undefined) {
    data.filename = model.filename;
  }
  return data;
}

@Component({
  selector: "app-machine-resolver-hosts-tab",
  templateUrl: "./machine-resolver-hosts-tab.component.html",
  styleUrls: ["./machine-resolver-hosts-tab.component.scss"],
  imports: [FormField, MatFormFieldModule, MatInputModule],
  standalone: true
})
export class MachineResolverHostsTabComponent {
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  readonly canEdit = input<boolean>(false);
  // The default data is read while the details page evaluates the validity of a tab whose inputs are not bound yet.
  readonly machineResolverData = input<MachineResolverData>({ resolver: "", type: "hosts" });
  readonly newData = output<MachineResolverData>();

  readonly model = linkedSignal<HostsFormModel>(() => toFormModel(this.machineResolverData()));
  readonly hostsForm = form(this.model, (f) => {
    requiredNonBlank(f.filename);
    disabled(f.filename, () => !this.canEdit());
  });

  readonly isValid = () => this.hostsForm().valid();
  readonly touchAll = () => touchAll(this.hostsForm);

  constructor() {
    effect(() => {
      const model = this.model();
      const base = untracked(() => this.machineResolverData());
      if (JSON.stringify(model) !== JSON.stringify(toFormModel(base))) {
        this.newData.emit(toData(model, base));
      }
    });
  }
}
