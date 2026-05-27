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

import { DatePipe } from "@angular/common";
import {
  AfterViewInit,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  OnDestroy,
  Renderer2,
  signal,
  untracked,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatExpansionPanel, MatExpansionPanelHeader, MatExpansionPanelTitle } from "@angular/material/expansion";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTooltip, MatTooltipModule } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  EMPTY_PERIODIC_TASK,
  PERIODIC_TASK_MODULE_MAPPING,
  PeriodicTask,
  PeriodicTaskModule,
  PeriodicTaskOption,
  PeriodicTaskService,
  PeriodicTaskServiceInterface
} from "@services/periodic-task/periodic-task.service";
import { SystemService } from "@services/system/system.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { parseBooleanValue } from "@utils/parse-boolean-value";
import { firstValueFrom } from "rxjs";

@Component({
  selector: "app-periodic-task-edit",
  standalone: true,
  imports: [
    ScrollToTopDirective,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatFormField,
    MatInput,
    MatOption,
    MatSelect,
    MatLabel,
    MatCheckbox,
    MatSlideToggle,
    MatHint,
    MatError,
    MatIcon,
    MatTooltip,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    FormField,
    ClearableInputComponent,
    CopyButtonComponent,
    DatePipe
  ],
  templateUrl: "./periodic-task-edit.component.html",
  styleUrl: "./periodic-task-edit.component.scss"
})
export class PeriodicTaskEditComponent implements AfterViewInit, OnDestroy {
  protected readonly periodicTaskService: PeriodicTaskServiceInterface = inject(PeriodicTaskService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly systemService = inject(SystemService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly renderer: Renderer2 = inject(Renderer2);

  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;

  private stickyObserver?: IntersectionObserver;

  protected readonly Object = Object;
  protected readonly parseBooleanValue = parseBooleanValue;

  isNewTask = signal<boolean>(false);
  editTask: WritableSignal<PeriodicTask> = signal<PeriodicTask>({ ...EMPTY_PERIODIC_TASK });

  readonly title = computed(() => (this.isNewTask() ? $localize`Create Periodic Task` : $localize`Edit Periodic Task`));

  private originalTask: PeriodicTask = { ...EMPTY_PERIODIC_TASK };
  private editName: string | null = null;

  editTaskForm = form(this.editTask, (f) => {
    required(f.name);
    pattern(f.name, /^[a-zA-Z0-9._-]*$/);
    required(f.interval);
  });

  taskModules: WritableSignal<PeriodicTaskModule[]> = linkedSignal({
    source: this.periodicTaskService.periodicTaskModuleResource.value,
    computation: (moduleResource) => moduleResource?.result?.value ?? []
  });

  taskModuleOptions = computed(() => this.periodicTaskService.moduleOptions()[this.editTask().taskmodule]);

  requiredOptions = computed(() => {
    const options = this.taskModuleOptions() || {};
    return Object.fromEntries(Object.entries(options).filter(([, opt]) => opt.required));
  });

  fieldHasError(field: { errors(): { kind: string }[]; dirty(): boolean; touched(): boolean }, kind: string): boolean {
    return field.errors().some((e) => e.kind === kind) && (field.dirty() || field.touched());
  }

  isOptionSet(key: string): boolean {
    return Object.prototype.hasOwnProperty.call(this.editTask().options, key);
  }

  isDateValue(value: unknown): boolean {
    if (typeof value !== "string" || value === "") return false;
    return !Number.isNaN(Date.parse(value));
  }

  toggleOption(key: string, opt: PeriodicTaskOption, checked: boolean): void {
    if (opt.required) return;
    const options = { ...this.editTask().options };
    if (checked) {
      options[key] = opt.type === "bool" ? "true" : opt.value ?? "";
    } else {
      delete options[key];
    }
    this.editTask.set({ ...this.editTask(), options });
  }

  updateOptionValue(key: string, value: string): void {
    this.editTask.set({
      ...this.editTask(),
      options: { ...this.editTask().options, [key]: value }
    });
  }

  canSave = computed(() => {
    const t = this.editTask();
    if (t.name === "" || !/^[a-zA-Z0-9._-]*$/.test(t.name)) return false;
    if (t.taskmodule === "") return false;
    if (t.interval === "") return false;
    if (t.nodes.length === 0) return false;
    if (t.ordering === null) return false;
    if (Object.keys(t.options).length === 0) return false;
    for (const key of Object.keys(this.requiredOptions())) {
      const v = t.options[key];
      if (v === undefined || v === null || v === "") return false;
    }
    return true;
  });

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave());

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const name = params.get("name");
      if (name) {
        this.isNewTask.set(false);
        this.editName = name;
        const found = this.findTaskByName(name);
        if (found) {
          this.loadTask(found);
        }
      } else {
        this.isNewTask.set(true);
        this.editName = null;
        this.loadTask({ ...EMPTY_PERIODIC_TASK });
      }
    });

    // Re-bind once the resource arrives (deep-link case).
    effect(() => {
      const resource = this.periodicTaskService.periodicTasksResource;
      if (resource.hasValue && !resource.hasValue()) return;
      if (this.isNewTask() || !this.editName) return;
      const found = this.findTaskByName(this.editName);
      if (found && untracked(() => !this.hasChanges())) {
        this.loadTask(found);
      }
    });

    this.periodicTaskService.fetchAllModuleOptions();
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;

    this.stickyObserver = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) return;
        const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
        if (shouldFloat) {
          this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
        } else {
          this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
        }
      },
      { root: this.scrollContainer.nativeElement, threshold: [0, 1] }
    );
    this.stickyObserver.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.stickyObserver?.disconnect();
  }

  hasChanges(): boolean {
    if (this.isNewTask()) {
      return JSON.stringify(this.editTask()) !== JSON.stringify(EMPTY_PERIODIC_TASK);
    }
    return JSON.stringify(this.editTask()) !== JSON.stringify(this.originalTask);
  }

  private loadTask(task: PeriodicTask): void {
    this.originalTask = task;
    this.editTask.set(deepCopy(task));
  }

  private findTaskByName(name: string): PeriodicTask | undefined {
    const resource = this.periodicTaskService.periodicTasksResource;
    if (resource.hasValue && !resource.hasValue()) return undefined;
    const tasks = resource.value()?.result?.value ?? [];
    return tasks.find((t) => t.name === name);
  }

  async save(): Promise<boolean> {
    if (!this.canSave()) return false;
    try {
      const response = await firstValueFrom(this.periodicTaskService.savePeriodicTask(this.editTask()));
      if (response?.result?.value !== undefined) {
        this.periodicTaskService.periodicTasksResource.reload();
        this.pendingChangesService.clearAllRegistrations();
        this.router.navigateByUrl(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  onCancel(): void {
    if (!this.hasChanges()) {
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          title: $localize`Discard changes`,
          allowSaveExit: true,
          saveExitDisabled: !this.canSave()
        }
      })
      .afterClosed()
      .subscribe(async (result) => {
        if (result === "discard") {
          this.pendingChangesService.clearAllRegistrations();
          this.router.navigateByUrl(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
        } else if (result === "save-exit") {
          if (!this.canSave()) return;
          await this.save();
        }
      });
  }

  // Form actions

  onNodeSelectionChange(nodes: string[]): void {
    this.editTask.set({ ...this.editTask(), nodes });
  }

  onTaskModuleChange(module: string): void {
    this.editTask.set({ ...this.editTask(), taskmodule: module });
    const required: Record<string, string> = {};
    Object.entries(this.requiredOptions()).forEach(([key, opt]) => {
      required[key] = opt.value ?? "";
    });
    this.editTask.set({ ...this.editTask(), options: { ...required } });
  }

  getModuleLabel(module: string): string {
    return PERIODIC_TASK_MODULE_MAPPING[module as PeriodicTaskModule] ?? module;
  }
}
