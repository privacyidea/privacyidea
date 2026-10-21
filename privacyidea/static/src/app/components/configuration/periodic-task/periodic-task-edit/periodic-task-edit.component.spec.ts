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

import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { EMPTY_PERIODIC_TASK, PeriodicTask, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { SystemService } from "@services/system/system.service";
import { MockAuthService, MockDialogService, MockPiResponse } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { expectedLocalDateTimeFromInput } from "@testing/expected-local-date-time";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of, throwError } from "rxjs";
import { PeriodicTaskEditComponent } from "./periodic-task-edit.component";

describe("PeriodicTaskEditComponent", () => {
  let periodicTaskService: MockPeriodicTaskService;
  let dialogService: MockDialogService;
  let pendingChangesService: MockPendingChangesService;
  let router: Router;

  const createComponent = async (paramMap: Record<string, string>, tasks: PeriodicTask[] = [], canWrite = false) => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskEditComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap(paramMap)) } },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    (TestBed.inject(AuthService) as unknown as MockAuthService).actionAllowed.mockReturnValue(canWrite);
    periodicTaskService = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
    if (tasks.length > 0) periodicTaskService.setPeriodicTasks(tasks);
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    const fixture: ComponentFixture<PeriodicTaskEditComponent> = TestBed.createComponent(PeriodicTaskEditComponent);
    return { fixture, component: fixture.componentInstance };
  };

  const VALID_TASK: PeriodicTask = {
    ...EMPTY_PERIODIC_TASK,
    id: 42,
    name: "nightly-stats",
    interval: "5 0 * * *",
    nodes: ["node-a"],
    taskmodule: "EventCounter",
    options: { event_counter: "logins", stats_key: "k" }
  };

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("Route handling", () => {
    it("initializes in create mode when no name param is present", async () => {
      const { component } = await createComponent({});
      expect(component.isNewTask()).toBe(true);
      expect(component.editTask().name).toBe("");
      expect(component.title()).toBe("Create Periodic Task");
    });

    it("initializes in edit mode when a name param is present", async () => {
      const { component } = await createComponent({ name: "my-task" });
      expect(component.isNewTask()).toBe(false);
      expect(component.title()).toBe("Edit Periodic Task");
    });
  });

  describe("Navigation actions", () => {
    it("onCancel navigates back to the table when there are no changes", async () => {
      const { component } = await createComponent({});
      component.onCancel();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
    });

    it("save is a no-op and does not navigate when canSave is false", async () => {
      const { component } = await createComponent({});
      expect(component.canSave()).toBe(false);
      const result = await component.save();
      expect(result).toBe(false);
      expect(periodicTaskService.savePeriodicTask).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });

  describe("Options handling", () => {
    const seedTask = (component: PeriodicTaskEditComponent) => {
      component.editTask.set({
        ...EMPTY_PERIODIC_TASK,
        id: 1,
        name: "Test Task",
        active: true,
        interval: "*/5 * * * *",
        nodes: ["node1"],
        taskmodule: "SimpleStats",
        retry_if_failed: true,
        ordering: 0,
        options: { hardware_tokens: "true", user_with_token: "true" }
      });
    };

    it("toggleOption adds a bool option with value 'true' when checked", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      const before = { ...component.editTask().options };
      component.toggleOption("new_bool", { name: "new_bool", description: "", type: "bool" }, true);
      expect(component.editTask().options["new_bool"]).toBe("true");
      // existing options are preserved
      expect(component.editTask().options["hardware_tokens"]).toBe(before["hardware_tokens"]);
    });

    it("toggleOption adds a non-bool option with the option's default value", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.toggleOption(
        "stats_key",
        { name: "stats_key", description: "", type: "str", value: "default-key" },
        true
      );
      expect(component.editTask().options["stats_key"]).toBe("default-key");
    });

    it("toggleOption falls back to empty string for non-bool options without a default", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.toggleOption("stats_key", { name: "stats_key", description: "", type: "str" }, true);
      expect(component.editTask().options["stats_key"]).toBe("");
    });

    it("toggleOption removes the option when unchecked", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.toggleOption("hardware_tokens", { name: "hardware_tokens", description: "", type: "bool" }, false);
      expect(component.editTask().options).not.toHaveProperty("hardware_tokens");
    });

    it("toggleOption refuses to toggle a required option (lock-on)", async () => {
      const { component } = await createComponent({});
      component.editTask.set({
        ...EMPTY_PERIODIC_TASK,
        taskmodule: "EventCounter",
        options: { event_counter: "logins" }
      });
      component.toggleOption(
        "event_counter",
        { name: "event_counter", description: "", type: "str", required: true },
        false
      );
      expect(component.editTask().options["event_counter"]).toBe("logins");
    });

    it("isOptionSet returns true only for keys present in editTask.options", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      expect(component.isOptionSet("hardware_tokens")).toBe(true);
      expect(component.isOptionSet("not_in_options")).toBe(false);
    });

    it("replaces the options with the new module's required defaults on module change", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.onTaskModuleChange("EventCounter");
      expect(component.editTask().options).toEqual({ event_counter: "", stats_key: "" });
      component.onTaskModuleChange("UnknownModule");
      expect(component.editTask().options).toEqual({});
    });

    it("computes requiredOptions correctly", async () => {
      const { component } = await createComponent({});
      component.editTask.set({ ...EMPTY_PERIODIC_TASK, taskmodule: "EventCounter", options: {} });
      const required = component.requiredOptions();
      expect(Object.keys(required)).toEqual(["event_counter", "stats_key"]);
    });

    it("preselects required options on module change for new task", async () => {
      const { component } = await createComponent({});
      component.editTask.set({ ...EMPTY_PERIODIC_TASK, taskmodule: "EventCounter", options: {} });
      component.onTaskModuleChange("EventCounter");
      const options = component.editTask().options;
      expect(options).toHaveProperty("event_counter");
      expect(options).toHaveProperty("stats_key");
      expect(options["event_counter"]).toBe("");
      expect(options["stats_key"]).toBe("");
    });
  });

  describe("canSave", () => {
    it("is false when a required option is missing", async () => {
      const { component } = await createComponent({});
      component.onTaskModuleChange("EventCounter");
      component.editTask.set({ ...component.editTask(), options: { event_counter: "test" } });
      expect(component.canSave()).toBe(false);
    });

    it("is false when a required option value is empty", async () => {
      const { component } = await createComponent({});
      component.onTaskModuleChange("EventCounter");
      component.editTask.set({ ...component.editTask(), options: { event_counter: "test", stats_key: "" } });
      expect(component.canSave()).toBe(false);
    });

    it("is false when name is missing", async () => {
      const { component } = await createComponent({});
      component.editTask.set({ ...component.editTask(), name: "" });
      expect(component.canSave()).toBe(false);
    });

    it("is false when interval is missing", async () => {
      const { component } = await createComponent({});
      component.editTask.set({ ...component.editTask(), interval: "" });
      expect(component.canSave()).toBe(false);
    });

    it("is false when options are empty", async () => {
      const { component } = await createComponent({});
      component.editTask.set({ ...component.editTask(), options: {} });
      expect(component.canSave()).toBe(false);
    });

    it("is true when all required fields and options are set", async () => {
      const { component } = await createComponent({});
      component.editTask.set({
        ...EMPTY_PERIODIC_TASK,
        name: "Task",
        interval: "* * * * *",
        nodes: ["node1"],
        ordering: 1,
        taskmodule: "EventCounter",
        options: { event_counter: "val1", stats_key: "val2" }
      });
      expect(component.canSave()).toBe(true);
    });
  });

  describe("Route handling with seeded resource", () => {
    it("loads the task into editTask when the route name matches one in the resource", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      expect(component.isNewTask()).toBe(false);
      expect(component.editTask().name).toBe(VALID_TASK.name);
      expect(component.editTask().interval).toBe(VALID_TASK.interval);
      expect(component.editTask().options).toEqual(VALID_TASK.options);
    });

    it("hasChanges is false right after a task is loaded (editTask matches originalTask)", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      expect(component.hasChanges()).toBe(false);
    });

    it("hasChanges is true once editTask diverges from the loaded original", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.editTask.set({ ...component.editTask(), interval: "*/10 * * * *" });
      expect(component.hasChanges()).toBe(true);
    });
  });

  describe("onTaskModuleChange in edit mode", () => {
    it("resets options to required-only when the module changes in edit mode", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.onTaskModuleChange("SimpleStats");
      // SimpleStats has no required options, so options should be cleared entirely
      expect(component.editTask().options).toEqual({});

      // Switching to EventCounter pre-fills its two required options with empty strings
      component.onTaskModuleChange("EventCounter");
      expect(component.editTask().options).toEqual({ event_counter: "", stats_key: "" });
    });

    it("preserves non-option fields (interval, nodes, name) when the module changes", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.onTaskModuleChange("SimpleStats");
      expect(component.editTask().interval).toBe(VALID_TASK.interval);
      expect(component.editTask().nodes).toEqual(VALID_TASK.nodes);
      expect(component.editTask().name).toBe(VALID_TASK.name);
    });
  });

  describe("getModuleLabel", () => {
    it("returns the mapped label for a known module", async () => {
      const { component } = await createComponent({});
      expect(component.getModuleLabel("SimpleStats")).toBe("Simple Statistics");
      expect(component.getModuleLabel("EventCounter")).toBe("Event Counter");
    });

    it("falls back to the raw value for an unknown module", async () => {
      const { component } = await createComponent({});
      expect(component.getModuleLabel("MysteryModule")).toBe("MysteryModule");
    });
  });

  describe("save", () => {
    it("calls savePeriodicTask, reloads the resource, clears pending changes, and navigates", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      const result = await component.save();
      expect(result).toBe(true);
      expect(periodicTaskService.savePeriodicTask).toHaveBeenCalledWith(component.editTask());
      expect(periodicTaskService.periodicTasksResource.reload).toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
    });

    it("returns false and does not navigate when the service returns a response without a result value", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      (periodicTaskService.savePeriodicTask as jest.Mock).mockReturnValueOnce(of({ result: { value: undefined } }));
      const result = await component.save();
      expect(result).toBe(false);
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("returns false and does not navigate when the service throws", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      (periodicTaskService.savePeriodicTask as jest.Mock).mockReturnValueOnce(throwError(() => new Error("boom")));
      const result = await component.save();
      expect(result).toBe(false);
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });

  describe("onCancel with pending changes", () => {
    it("navigates back when the user picks 'discard' in the dialog", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.editTask.set({ ...component.editTask(), interval: "*/2 * * * *" });
      (dialogService.openDialog as jest.Mock).mockReturnValueOnce({ afterClosed: () => of("discard") });
      component.onCancel();
      // afterClosed callback runs synchronously in this mock; let microtasks flush
      await Promise.resolve();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
    });

    it("triggers save when the user picks 'save-exit' and canSave is true", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.editTask.set({ ...component.editTask(), interval: "*/3 * * * *" });
      (dialogService.openDialog as jest.Mock).mockReturnValueOnce({ afterClosed: () => of("save-exit") });
      component.onCancel();
      await Promise.resolve();
      await Promise.resolve();
      expect(periodicTaskService.savePeriodicTask).toHaveBeenCalled();
    });

    it("is a no-op for 'save-exit' when canSave is false", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.editTask.set({ ...component.editTask(), interval: "" });
      (dialogService.openDialog as jest.Mock).mockReturnValueOnce({ afterClosed: () => of("save-exit") });
      component.onCancel();
      await Promise.resolve();
      expect(periodicTaskService.savePeriodicTask).not.toHaveBeenCalled();
    });
  });

  describe("Form rules", () => {
    const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

    it("requires a name made of identifier characters", async () => {
      const { component } = await createComponent({});
      const name = component.editTaskForm.name;
      expect(kinds(name())).toEqual(["required"]);
      component.editTask.update((t) => ({ ...t, name: "bad name!" }));
      expect(kinds(name())).toEqual(["pattern"]);
      component.editTask.update((t) => ({ ...t, name: "good.name-1_x" }));
      expect(name().errors()).toEqual([]);
    });

    it("requires a task module and an interval", async () => {
      const { component } = await createComponent({});
      component.editTask.update((t) => ({ ...t, taskmodule: "" }));
      expect(kinds(component.editTaskForm.taskmodule())).toEqual(["required"]);
      expect(kinds(component.editTaskForm.interval())).toEqual(["required"]);
      component.editTask.update((t) => ({ ...t, taskmodule: "SimpleStats", interval: "* * * * *" }));
      expect(component.editTaskForm.taskmodule().errors()).toEqual([]);
      expect(component.editTaskForm.interval().errors()).toEqual([]);
    });

    it("requires at least one node", async () => {
      const { component } = await createComponent({});
      expect(kinds(component.editTaskForm.nodes())).toEqual(["required"]);
      component.editTask.update((t) => ({ ...t, nodes: ["node-a"] }));
      expect(component.editTaskForm.nodes().errors()).toEqual([]);
    });

    it("accepts an ordering of 0 and rejects an empty ordering", async () => {
      const { component } = await createComponent({});
      expect(component.editTaskForm.ordering().errors()).toEqual([]);
      component.editTask.update((t) => ({ ...t, ordering: null }));
      expect(kinds(component.editTaskForm.ordering())).toEqual(["required"]);
      component.editTask.update((t) => ({ ...t, ordering: 7 }));
      expect(component.editTaskForm.ordering().errors()).toEqual([]);
    });

    it("rejects an empty options map and accepts a module without required options", async () => {
      const { component } = await createComponent({});
      expect(kinds(component.editTaskForm.options())).toEqual(["required"]);
      component.editTask.update((t) => ({ ...t, taskmodule: "SimpleStats", options: { hardware_tokens: "true" } }));
      expect(component.editTaskForm.options().errors()).toEqual([]);
    });

    it("reports a missing required option on the options map", async () => {
      const { component } = await createComponent({});
      component.editTask.update((t) => ({ ...t, taskmodule: "EventCounter", options: { event_counter: "x" } }));
      expect(kinds(component.editTaskForm.options())).toEqual(["required"]);
    });

    it("reports an empty required option on its own field, but not an empty optional one", async () => {
      const { component } = await createComponent({});
      component.onTaskModuleChange("EventCounter");
      component.editTask.update((t) => ({
        ...t,
        taskmodule: "EventCounter",
        options: { ...t.options, reset_event_counter: "" }
      }));
      expect(kinds(component.editTaskForm.options["event_counter"]())).toEqual(["required"]);
      expect(kinds(component.editTaskForm.options["stats_key"]())).toEqual(["required"]);
      expect(component.editTaskForm.options["reset_event_counter"]().errors()).toEqual([]);
      component.editTask.update((t) => ({ ...t, options: { event_counter: "a", stats_key: "b" } }));
      expect(component.editTaskForm.options["event_counter"]().errors()).toEqual([]);
      expect(component.editTaskForm.options().errors()).toEqual([]);
    });

    it("disables the active toggle without the periodictask_write right", async () => {
      const { component } = await createComponent({});
      expect(component.editTaskForm.active().disabled()).toBe(true);
    });

    it("enables the active toggle with the periodictask_write right", async () => {
      const { component } = await createComponent({}, [], true);
      expect(component.editTaskForm.active().disabled()).toBe(false);
    });

    it("does not let the disabled active toggle block saving", async () => {
      const { component } = await createComponent({});
      component.editTask.set({ ...VALID_TASK, ordering: 1 });
      expect(component.editTaskForm.active().disabled()).toBe(true);
      expect(component.canSave()).toBe(true);
    });
  });

  describe("Template bindings", () => {
    const inputs = (fixture: ComponentFixture<PeriodicTaskEditComponent>) =>
      Array.from(fixture.nativeElement.querySelectorAll("input[matInput]")) as HTMLInputElement[];

    const type = async (
      fixture: ComponentFixture<PeriodicTaskEditComponent>,
      field: HTMLInputElement,
      value: string
    ) => {
      field.value = value;
      field.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    const flush = async (fixture: ComponentFixture<PeriodicTaskEditComponent>) => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    const errorTexts = (fixture: ComponentFixture<PeriodicTaskEditComponent>) =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) =>
        (e as HTMLElement).textContent?.replace(/\s+/g, " ").trim()
      );

    it("writes typed name, interval and ordering into the model", async () => {
      const { fixture, component } = await createComponent({});
      await flush(fixture);
      const [name, interval, ordering] = inputs(fixture);
      await type(fixture, name, "my-task");
      await type(fixture, interval, "5 0 * * *");
      await type(fixture, ordering, "12");
      expect(component.editTask().name).toBe("my-task");
      expect(component.editTask().interval).toBe("5 0 * * *");
      expect(component.editTask().ordering).toBe(12);
      expect(component.editTaskForm.name().dirty()).toBe(true);
    });

    it("stores an emptied ordering as null and renders the required message once touched", async () => {
      const { fixture, component } = await createComponent({});
      await flush(fixture);
      const ordering = inputs(fixture)[2];
      await type(fixture, ordering, "");
      expect(component.editTask().ordering).toBeNull();
      ordering.dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(errorTexts(fixture)).toContain("Ordering is required.");
    });

    it("renders the parse message for text the number input cannot parse", async () => {
      const { fixture, component } = await createComponent({});
      await flush(fixture);
      const ordering = inputs(fixture)[2];
      jest.spyOn(ordering, "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
      await type(fixture, ordering, "");
      expect(
        component.editTaskForm
          .ordering()
          .errors()
          .map((e) => e.kind)
      ).toContain("parse");
      ordering.dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(errorTexts(fixture)).toContain("Ordering has to be a number.");
    });

    it("clears the name and interval through the clear buttons", async () => {
      const { fixture, component } = await createComponent({});
      component.editTask.update((t) => ({ ...t, name: "abc", interval: "* * * * *" }));
      await flush(fixture);
      const clearables = fixture.debugElement.queryAll(By.directive(ClearableInputComponent));
      clearables[0].componentInstance.clearButtonClick.emit();
      clearables[1].componentInstance.clearButtonClick.emit();
      await flush(fixture);
      expect(component.editTask().name).toBe("");
      expect(component.editTask().interval).toBe("");
      expect(component.editTaskForm.name().dirty()).toBe(true);
    });

    it("renders the name errors after the name was edited", async () => {
      const { fixture } = await createComponent({});
      await flush(fixture);
      const name = inputs(fixture)[0];
      await type(fixture, name, "bad name");
      name.dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(errorTexts(fixture).some((t) => t?.startsWith("Name contains invalid characters"))).toBe(true);
      await type(fixture, name, "");
      expect(errorTexts(fixture)).toContain("Name is required.");
    });

    it("touches every field when a save is refused so the errors render", async () => {
      const { fixture, component } = await createComponent({});
      await flush(fixture);
      expect(errorTexts(fixture)).toEqual([]);
      expect(await component.save()).toBe(false);
      await flush(fixture);
      expect(component.editTaskForm.interval().touched()).toBe(true);
      const texts = errorTexts(fixture);
      expect(texts).toContain("Name is required.");
      expect(texts).toContain("Interval is required.");
      expect(texts).toContain("At least one node is required.");
    });

    it("binds the retry checkbox and the active toggle", async () => {
      const { fixture, component } = await createComponent({}, [], true);
      await flush(fixture);
      const retry = fixture.nativeElement.querySelector(".server-checkbox input[type=checkbox]") as HTMLInputElement;
      retry.click();
      await flush(fixture);
      expect(component.editTask().retry_if_failed).toBe(!EMPTY_PERIODIC_TASK.retry_if_failed);
      const toggle = fixture.nativeElement.querySelector("mat-slide-toggle button") as HTMLButtonElement;
      expect(toggle.disabled).toBe(false);
      toggle.click();
      await flush(fixture);
      expect(component.editTask().active).toBe(!EMPTY_PERIODIC_TASK.active);
    });

    it("disables the active toggle without the write right", async () => {
      const { fixture } = await createComponent({});
      await flush(fixture);
      const toggle = fixture.nativeElement.querySelector("mat-slide-toggle button") as HTMLButtonElement;
      expect(toggle.disabled).toBe(true);
    });

    it("writes the selected module and nodes into the model", async () => {
      const { fixture, component } = await createComponent({});
      periodicTaskService.periodicTaskModuleResource.value.set(
        MockPiResponse.fromValue(["EventCounter", "SimpleStats"] as never)
      );
      await flush(fixture);
      const selects = fixture.debugElement.queryAll(By.directive(MatSelect));
      const [moduleSelect, nodesSelect] = selects.map((s) => s.componentInstance as MatSelect);
      moduleSelect.open();
      await flush(fixture);
      (document.querySelectorAll("mat-option")[0] as HTMLElement).click();
      await flush(fixture);
      expect(component.editTask().taskmodule).toBe("EventCounter");
      expect(component.editTask().options).toEqual({ event_counter: "", stats_key: "" });
      nodesSelect.open();
      await flush(fixture);
      const optionByText = (text: string) =>
        Array.from(document.querySelectorAll("mat-option")).find((o) => o.textContent?.trim() === text) as HTMLElement;
      optionByText("Node 2").click();
      await flush(fixture);
      expect(component.editTask().nodes).toEqual(["Node 2"]);
    });

    it("writes an option value into the options map and flags an emptied required option", async () => {
      const { fixture, component } = await createComponent({});
      component.editTask.update((t) => ({ ...t, taskmodule: "EventCounter" }));
      component.onTaskModuleChange("EventCounter");
      await flush(fixture);
      const valueInputs = inputs(fixture).slice(3);
      expect(valueInputs).toHaveLength(2);
      await type(fixture, valueInputs[0], "logins");
      expect(component.editTask().options["event_counter"]).toBe("logins");
      await type(fixture, valueInputs[0], "");
      valueInputs[0].dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(errorTexts(fixture)).toContain("Value is required.");
    });
  });

  describe("Optional option toggle", () => {
    it("adds an optional text option through its checkbox and binds its value input", async () => {
      const { fixture, component } = await createComponent({}, [], true);
      periodicTaskService.moduleOptions.update((modules) => ({
        ...modules,
        EventCounter: {
          ...modules["EventCounter"],
          note: { name: "note", description: "Free text", type: "str" }
        }
      }));
      component.editTask.update((t) => ({ ...t, taskmodule: "EventCounter" }));
      component.onTaskModuleChange("EventCounter");
      await fixture.whenStable();
      fixture.detectChanges();
      const checkbox = fixture.nativeElement.querySelector('input[aria-label="note"]') as HTMLInputElement;
      checkbox.click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
      expect(component.isOptionSet("note")).toBe(true);
      const valueInputs = Array.from(fixture.nativeElement.querySelectorAll("input[matInput]")) as HTMLInputElement[];
      const last = valueInputs[valueInputs.length - 1];
      last.value = "hello";
      last.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      expect(component.editTask().options["note"]).toBe("hello");
      expect(component.editTaskForm.options["note"]().dirty()).toBe(true);
    });
  });

  describe("Dirty tracking", () => {
    it("starts clean after loading a task and keeps hasChanges in step with edits", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      expect(component.editTaskForm().dirty()).toBe(false);
      expect(component.hasChanges()).toBe(false);
      component.editTaskForm.interval().controlValue.set("*/9 * * * *");
      expect(component.hasChanges()).toBe(true);
      component.editTaskForm.interval().controlValue.set(VALID_TASK.interval);
      expect(component.hasChanges()).toBe(false);
    });

    it("loads a task that arrives after the page opened and clears dirty", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name });
      expect(component.editTask().name).toBe("");
      periodicTaskService.setPeriodicTasks([VALID_TASK]);
      TestBed.tick();
      expect(component.editTask().name).toBe(VALID_TASK.name);
      expect(component.editTaskForm().dirty()).toBe(false);
    });

    it("does not overwrite edits when the task list reloads", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      component.editTaskForm.interval().controlValue.set("*/9 * * * *");
      periodicTaskService.setPeriodicTasks([{ ...VALID_TASK }]);
      TestBed.tick();
      expect(component.editTask().interval).toBe("*/9 * * * *");
    });
  });

  describe("Template rendering", () => {
    it("renders last_update and last_runs as local date/time, not the raw fixed format", async () => {
      const task: PeriodicTask = {
        ...VALID_TASK,
        last_update: "2026-01-15T10:00:00",
        last_runs: { "node-a": "2026-01-16T11:30:00" }
      };
      const { fixture, component } = await createComponent({ name: task.name }, [task]);
      fixture.detectChanges();

      const metadataRows = fixture.nativeElement.querySelectorAll(".metadata-row");
      expect(metadataRows[0].textContent).toContain(expectedLocalDateTimeFromInput("2026-01-15T10:00:00"));
      expect(metadataRows[1].textContent).toContain(expectedLocalDateTimeFromInput("2026-01-16T11:30:00"));
      expect(metadataRows[0].textContent).not.toContain("2026-01-15T10:00:00");
      expect(component.isDateValue("2026-01-16T11:30:00")).toBe(true);
    });
  });

  describe("deleteTask", () => {
    it("does not offer deletion while the task list is unresolved", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name });
      expect(component.taskExists()).toBe(false);
    });

    it("offers deletion once the task is present in the list", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      expect(component.taskExists()).toBe(true);
    });

    it("does nothing in create mode", async () => {
      const { component } = await createComponent({});
      await component.deleteTask();
      expect(periodicTaskService.deleteWithConfirmDialog).not.toHaveBeenCalled();
    });

    it("does nothing when the loaded task has no id", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [
        { ...VALID_TASK, id: null as unknown as number }
      ]);
      await component.deleteTask();
      expect(periodicTaskService.deleteWithConfirmDialog).not.toHaveBeenCalled();
    });

    it("stays on the page when the deletion is not confirmed", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      periodicTaskService.deleteWithConfirmDialog.mockResolvedValue(undefined);
      await component.deleteTask();
      expect(periodicTaskService.deleteWithConfirmDialog).toHaveBeenCalledWith(
        expect.objectContaining({ id: VALID_TASK.id, name: VALID_TASK.name })
      );
      expect(periodicTaskService.periodicTasksResource.reload).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("reloads the tasks and navigates back after deleting", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      periodicTaskService.deleteWithConfirmDialog.mockResolvedValue(MockPiResponse.fromValue(1));
      await component.deleteTask();
      expect(periodicTaskService.periodicTasksResource.reload).toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
    });
  });
});
