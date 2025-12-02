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

import {
  Component,
  computed,
  EventEmitter,
  inject,
  input,
  linkedSignal,
  Output,
  Signal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import {
  EMPTY_PERIODIC_TASK,
  EMPTY_PERIODIC_TASK_OPTION,
  PeriodicTask,
  PeriodicTaskOption,
  PeriodicTaskService
} from "../../../../../services/periodic-task/periodic-task.service";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { SystemService } from "../../../../../services/system/system.service";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { parseBooleanValue } from "../../../../../utils/parse-boolean-value";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { PeriodicTaskOptionDetailComponent } from "./periodic-task-option-detail/periodic-task-option-detail.component";

@Component({
  selector: "app-periodic-task-edit",
  imports: [
    MatFormField,
    MatInput,
    FormsModule,
    MatOption,
    MatSelect,
    MatLabel,
    MatCheckbox,
    MatHint,
    MatIcon,
    MatIconButton,
    PeriodicTaskOptionDetailComponent
  ],
  templateUrl: "./periodic-task-edit.component.html",
  styleUrl: "./periodic-task-edit.component.scss"
})
export class PeriodicTaskEditComponent {
  private readonly systemService = inject(SystemService);
  private readonly periodicTaskService = inject(PeriodicTaskService);

  isNewTask = input<boolean>(false);
  task = input<PeriodicTask>(EMPTY_PERIODIC_TASK);

  @Output() editedTask = new EventEmitter<PeriodicTask>();

  emitEditedTask() {
    this.editedTask.emit(this.editTask());
  }

  @ViewChild(PeriodicTaskOptionDetailComponent) optionDetailComponent!: PeriodicTaskOptionDetailComponent;

  editTask = linkedSignal(this.task);
  newOptionValues: WritableSignal<Record<string, string>> = signal({});
  editOption = signal("");

  protected readonly Object = Object;
  protected readonly parseBooleanValue = parseBooleanValue;

  notUsedOptions: Signal<Record<string, PeriodicTaskOption>> = computed(() => {
      const allOptions = this.taskModuleOptions() || {};
      const usedOptionKeys = Object.keys(this.editTask().options || {});
      return Object.fromEntries(
        Object.entries(allOptions)
          .filter(([key]) => !usedOptionKeys.includes(key)));
    }
  );

  selectedOption = linkedSignal(() => {
    if (Object.keys(this.editTask().options).length > 0) {
      const firstKey = Object.keys(this.editTask().options)[0];
      let options = this.taskModuleOptions()[firstKey];
      options["value"] = this.editTask().options[firstKey];
      return options;
    } else if (Object.keys(this.notUsedOptions()).length > 0) {
      const firstKey = Object.keys(this.notUsedOptions())[0];
      return this.notUsedOptions()[firstKey];
    }
    return EMPTY_PERIODIC_TASK_OPTION;
  });

  taskModules: WritableSignal<any> = linkedSignal({
    source: this.periodicTaskService.periodicTaskModuleResource.value,
    computation: (moduleResource) => {
      if (moduleResource) {
        return moduleResource?.result?.value;
      }
      return [];
    }
  });

  taskModuleOptions = computed(() => this.periodicTaskService.moduleOptions()[this.editTask().taskmodule]);

  nodes = computed(() => {
    const nodes = this.systemService.nodes();
    return [
      ...nodes.map((n) => ({
        label: n.name,
        value: n.uuid
      }))
    ];
  });

  onNodeSelectionChange(nodes: string[]) {
    this.editTask.set({ ...this.editTask(), nodes });
  }

  onTaskModuleChange(module: string) {
    this.editTask.set({ ...this.editTask(), taskmodule: module });
  }

  onOptionSelection(optionName: string, option: PeriodicTaskOption, value?: string) {
    this.selectedOption.set({ ...option, name: optionName, value: value || "" });
  }

  isBooleanAction(param: any) {
    return ["true", "false"].includes(String(param).toLowerCase());
  }

  addOption(value: string): void {
    const optionName = this.selectedOption().name;
    if (!optionName) return;
    const newOptions = { ...this.editTask().options, [optionName]: value };
    this.editTask.set({ ...this.editTask(), options: newOptions });
  }

  deleteOption(optionKey: string) {
    const options = { ...this.editTask().options };
    delete options[optionKey];
    this.editTask.set({ ...this.editTask(), options });
  }
}
