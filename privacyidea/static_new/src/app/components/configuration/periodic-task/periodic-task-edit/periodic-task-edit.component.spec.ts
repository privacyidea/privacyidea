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
import { EMPTY_PERIODIC_TASK, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { SystemService } from "@services/system/system.service";
import { MockAuthService, MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of } from "rxjs";
import { PeriodicTaskEditComponent } from "./periodic-task-edit.component";

describe("PeriodicTaskEditComponent", () => {
  let periodicTaskService: PeriodicTaskService;
  let router: Router;

  const createComponent = async (paramMap: Record<string, string>) => {
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

    periodicTaskService = TestBed.inject(PeriodicTaskService);
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    const fixture: ComponentFixture<PeriodicTaskEditComponent> = TestBed.createComponent(PeriodicTaskEditComponent);
    return { fixture, component: fixture.componentInstance };
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

    it("selects an option", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.onOptionSelection("total_tokens", { name: "total_tokens", description: "", type: "bool" });
      expect(component.selectedOption().name).toBe("total_tokens");
      expect(component.selectedOption().value).toBe("");
    });

    it("adds an option", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.selectedOption.set({ name: "total_tokens", description: "", type: "bool" });
      component.addOption("true");
      expect(component.editTask().options["total_tokens"]).toBe("true");
    });

    it("deletes an option", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.deleteOption("hardware_tokens");
      expect(component.editTask().options["hardware_tokens"]).toBeUndefined();
    });

    it("detects boolean values", async () => {
      const { component } = await createComponent({});
      expect(component.isBooleanAction("true")).toBe(true);
      expect(component.isBooleanAction("false")).toBe(true);
      expect(component.isBooleanAction("TRUE")).toBe(true);
      expect(component.isBooleanAction("False")).toBe(true);
      expect(component.isBooleanAction("yes")).toBe(false);
      expect(component.isBooleanAction("")).toBe(false);
    });

    it("updates nodes on selection change", async () => {
      const { component } = await createComponent({});
      seedTask(component);
      component.onNodeSelectionChange(["node1", "node2"]);
      expect(component.editTask().nodes).toEqual(["node1", "node2"]);
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
});