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
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { EMPTY_PERIODIC_TASK, PeriodicTask, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { SystemService } from "@services/system/system.service";
import { MockAuthService, MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of, throwError } from "rxjs";
import { PeriodicTaskEditComponent } from "./periodic-task-edit.component";

describe("PeriodicTaskEditComponent", () => {
  let periodicTaskService: MockPeriodicTaskService;
  let dialogService: MockDialogService;
  let pendingChangesService: MockPendingChangesService;
  let router: Router;

  const createComponent = async (paramMap: Record<string, string>, tasks: PeriodicTask[] = []) => {
    const periodicTaskMock = new MockPeriodicTaskService();
    if (tasks.length > 0) periodicTaskMock.setPeriodicTasks(tasks);

    await TestBed.configureTestingModule({
      imports: [PeriodicTaskEditComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap(paramMap)) } },
        { provide: PeriodicTaskService, useValue: periodicTaskMock },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    periodicTaskService = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
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
    });

    it("initializes in edit mode when a name param is present", async () => {
      const { component } = await createComponent({ name: "my-task" });
      expect(component.isNewTask()).toBe(false);
    });
  });

  describe("Navigation actions", () => {
    it("onCancel navigates back to the table when there are no changes", async () => {
      const { component } = await createComponent({});
      component.onCancel();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
    });

    it("onDelete is a no-op when the loaded task has no id", async () => {
      const { component } = await createComponent({ name: "my-task" });
      await component.onDelete();
      expect(periodicTaskService.deleteWithConfirmDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
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
      component.toggleOption(
        "hardware_tokens",
        { name: "hardware_tokens", description: "", type: "bool" },
        false
      );
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

    it("updateOptionValue sets the value for a single option without disturbing the rest", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      const before = { ...component.editTask().options };
      component.updateOptionValue("hardware_tokens", "false");
      expect(component.editTask().options["hardware_tokens"]).toBe("false");
      expect(component.editTask().options["user_with_token"]).toBe(before["user_with_token"]);
    });

    it("isOptionSet returns true only for keys present in editTask.options", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      expect(component.isOptionSet("hardware_tokens")).toBe(true);
      expect(component.isOptionSet("not_in_options")).toBe(false);
    });

    it("updates taskmodule on change", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.onTaskModuleChange("EventCounter");
      expect(component.editTask().taskmodule).toBe("EventCounter");
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
      expect(component.editTask().taskmodule).toBe("SimpleStats");
      // SimpleStats has no required options, so options should be cleared entirely
      expect(component.editTask().options).toEqual({});

      // Switching to EventCounter pre-fills its two required options with empty strings
      component.onTaskModuleChange("EventCounter");
      expect(component.editTask().taskmodule).toBe("EventCounter");
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

  describe("onNodeSelectionChange", () => {
    it("replaces the nodes array on the edit task", async () => {
      const { component } = await createComponent({});
      component.onNodeSelectionChange(["nodeA", "nodeB"]);
      expect(component.editTask().nodes).toEqual(["nodeA", "nodeB"]);
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
      (periodicTaskService.savePeriodicTask as jest.Mock).mockReturnValueOnce(
        throwError(() => new Error("boom"))
      );
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

  describe("onDelete with valid id", () => {
    it("calls deleteWithConfirmDialog, reloads, clears registrations, and navigates when confirmed", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      (periodicTaskService.deleteWithConfirmDialog as jest.Mock).mockResolvedValueOnce({
        result: { value: 1 }
      });
      await component.onDelete();
      expect(periodicTaskService.deleteWithConfirmDialog).toHaveBeenCalled();
      expect(periodicTaskService.periodicTasksResource.reload).toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
    });

    it("does nothing further when the dialog returns falsy", async () => {
      const { component } = await createComponent({ name: VALID_TASK.name }, [VALID_TASK]);
      (periodicTaskService.deleteWithConfirmDialog as jest.Mock).mockResolvedValueOnce(undefined);
      await component.onDelete();
      expect(periodicTaskService.deleteWithConfirmDialog).toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });
});