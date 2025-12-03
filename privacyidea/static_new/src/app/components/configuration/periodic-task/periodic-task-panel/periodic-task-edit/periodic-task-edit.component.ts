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
  PERIODIC_TASK_MODULE_MAPPING,
  PeriodicTask,
  PeriodicTaskModule,
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
import { MatTooltip } from "@angular/material/tooltip";
import { MatExpansionPanel, MatExpansionPanelHeader, MatExpansionPanelTitle } from "@angular/material/expansion";

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
    PeriodicTaskOptionDetailComponent,
    MatTooltip,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader
  ],
  templateUrl: "./periodic-task-edit.component.html",
  styleUrl: "./periodic-task-edit.component.scss"
})
export class PeriodicTaskEditComponent {
  private readonly systemService = inject(SystemService);
  private readonly periodicTaskService = inject(PeriodicTaskService);

  isNewTask = input<boolean>(false);
  task = input<PeriodicTask>(EMPTY_PERIODIC_TASK);

  @Output() allowSaveChanges = new EventEmitter<boolean>();

  emitAllowSave() {
    this.allowSaveChanges.emit(this.allowSave);
  }

  @ViewChild(PeriodicTaskOptionDetailComponent) optionDetailComponent!: PeriodicTaskOptionDetailComponent;

  editTask = linkedSignal(() => this.task());
  newOptionValues: WritableSignal<Record<string, string>> = signal({});
  editOption = signal("");

  protected readonly Object = Object;
  protected readonly parseBooleanValue = parseBooleanValue;

  // Add this computed signal for required options
  requiredOptions = computed(() => {
    const options = this.taskModuleOptions() || {};
    return Object.fromEntries(
      Object.entries(options).filter(([_, opt]) => opt.required)
    );
  });

  get allowSave() {
    if (this.editTask().name === "") return false;
    if (this.editTask().taskmodule === "") return false;
    if (this.editTask().interval === "") return false;
    if (this.editTask().nodes.length === 0) return false;
    if (this.editTask().ordering === null) return false;
    if (Object.keys(this.editTask().options).length == 0) return false;

    // Use requiredOptions signal for validation
    for (const key of Object.keys(this.requiredOptions())) {
      const value = this.editTask().options[key];
      if (value === undefined || value === null || value === "") {
        return false;
      }
    }

    return true;
  }

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

  taskModules: WritableSignal<PeriodicTaskModule[]> = linkedSignal({
    source: this.periodicTaskService.periodicTaskModuleResource.value,
    computation: (moduleResource) => {
      if (moduleResource?.result?.value) {
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
    this.emitAllowSave();
  }

  onTaskModuleChange(module: string) {
    this.editTask.set({ ...this.editTask(), taskmodule: module });

    // Preselect required options if creating a new task
    if (this.isNewTask()) {
      const requiredOptions: Record<string, any> = {};
      Object.entries(this.requiredOptions()).forEach(([key, opt]) => {
        requiredOptions[key] = opt.value ?? "";
      });
      this.editTask.set({
        ...this.editTask(),
        taskmodule: module,
        options: { ...requiredOptions }
      });
    }

    this.emitAllowSave();
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
    this.emitAllowSave();
  }

  deleteOption(optionKey: string) {
    const options = { ...this.editTask().options };
    delete options[optionKey];
    this.editTask.set({ ...this.editTask(), options });
    this.emitAllowSave();
  }

  getModuleLabel(module: string): string {
    return PERIODIC_TASK_MODULE_MAPPING[module as PeriodicTaskModule] ?? module;
  }
}
