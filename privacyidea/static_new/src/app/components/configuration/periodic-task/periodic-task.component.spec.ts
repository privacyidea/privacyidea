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
import { MatCheckboxChange } from "@angular/material/checkbox";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { EMPTY_PERIODIC_TASK, PeriodicTask, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockNotificationService } from "@testing/mock-services/mock-notification-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { of } from "rxjs";
import { PeriodicTaskComponent } from "./periodic-task.component";

describe("PeriodicTaskComponent", () => {
  let component: PeriodicTaskComponent;
  let fixture: ComponentFixture<PeriodicTaskComponent>;
  let periodicTaskService: MockPeriodicTaskService;
  let dialogService: MockDialogService;
  let notificationService: MockNotificationService;
  let router: Router;

  beforeEach(async () => {

    await TestBed.configureTestingModule({
      imports: [PeriodicTaskComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    periodicTaskService = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call fetchAllModuleOptions on ngOnInit", () => {
    const spy = jest.spyOn(periodicTaskService, "fetchAllModuleOptions");
    component.ngOnInit();
    expect(spy).toHaveBeenCalled();
  });

  it("should expose periodicTasks signal", () => {
    expect(component.periodicTasks).toBeDefined();
  });

  it("onCreateNewTask navigates to the new-task route", () => {
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.onCreateNewTask();
    expect(spy).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS_NEW);
  });

  it("onEditTask navigates to the task-details route by name", () => {
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, name: "my-task" };
    component.onEditTask(task);
    expect(spy).toHaveBeenCalledWith(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS_DETAILS + "my-task");
  });

  it("toggleActive enables the task when activate=true", () => {
    const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, id: 7 };
    component.toggleActive(task, true);
    expect(periodicTaskService.enablePeriodicTask).toHaveBeenCalledWith(7);
    expect(periodicTaskService.disablePeriodicTask).not.toHaveBeenCalled();
  });

  it("toggleActive disables the task when activate=false", () => {
    const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, id: 7 };
    component.toggleActive(task, false);
    expect(periodicTaskService.disablePeriodicTask).toHaveBeenCalledWith(7);
    expect(periodicTaskService.enablePeriodicTask).not.toHaveBeenCalled();
  });

  it("toggleActive is a no-op when the task has no id", () => {
    const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, id: null };
    component.toggleActive(task, true);
    expect(periodicTaskService.enablePeriodicTask).not.toHaveBeenCalled();
    expect(periodicTaskService.disablePeriodicTask).not.toHaveBeenCalled();
  });

  it("getModuleLabel returns the mapped label for known modules", () => {
    expect(component.getModuleLabel("SimpleStats")).toBe("Simple Statistics");
    expect(component.getModuleLabel("EventCounter")).toBe("Event Counter");
  });

  it("getModuleLabel falls back to the raw value for unknown modules", () => {
    expect(component.getModuleLabel("Unknown")).toBe("Unknown");
  });

  it("resetFilter clears the filter string", () => {
    component.filterString.set("abc");
    component.resetFilter();
    expect(component.filterString()).toBe("");
  });

  it("onFilterInput trims input, updates filterString, and applies it to the data source", () => {
    component.onFilterInput("  Logins  ");
    expect(component.filterString()).toBe("Logins");
    expect(component.periodicTasksDataSource().filter).toBe("logins");
  });

  it("onFilterInput treats nullish input as an empty string", () => {
    component.filterString.set("seed");
    component.onFilterInput(null as unknown as string);
    expect(component.filterString()).toBe("");
    expect(component.periodicTasksDataSource().filter).toBe("");
  });

  it("resetFilter clears the underlying input element value when one is present", () => {
    const inputElement = document.createElement("input");
    inputElement.value = "stale";
    (component as unknown as { filterInput: { nativeElement: HTMLInputElement } }).filterInput = {
      nativeElement: inputElement
    };
    component.filterString.set("stale");
    component.resetFilter();
    expect(inputElement.value).toBe("");
  });

  it("periodicTasks returns an empty array when the resource has no value", () => {
    periodicTaskService.periodicTasksResource.value.set(undefined);
    expect(component.periodicTasks()).toEqual([]);
  });

  it("isAllSelected is false when there are no selectable tasks at all", () => {
    // default mock state: resource value is an empty list → no selectable ids
    expect(component.isAllSelected()).toBe(false);
  });

  describe("matchesFilter", () => {
    const task: PeriodicTask = {
      ...EMPTY_PERIODIC_TASK,
      id: 1,
      name: "nightly-stats",
      interval: "5 0 * * *",
      nodes: ["node-a", "node-b"],
      taskmodule: "EventCounter",
      active: true,
      options: { total_tokens: "true", event_counter: "logins" }
    };

    it("treats a missing nodes array as empty (no match against 'undefined')", () => {
      const t = { ...task, nodes: undefined as unknown as string[] };
      expect(component.matchesFilter(t, "undefined")).toBe(false);
      expect(component.matchesFilter(t, "nightly")).toBe(true);
    });

    it("matches on the task name", () => {
      expect(component.matchesFilter(task, "nightly")).toBe(true);
    });

    it("matches on the human-readable task module label", () => {
      expect(component.matchesFilter(task, "event counter")).toBe(true);
    });

    it("matches on a node name", () => {
      expect(component.matchesFilter(task, "node-b")).toBe(true);
    });

    it("matches on an option key for a boolean flag option", () => {
      expect(component.matchesFilter(task, "total_tokens")).toBe(true);
    });

    it("matches on a non-boolean option value", () => {
      expect(component.matchesFilter(task, "logins")).toBe(true);
    });

    it("matches on the active status text", () => {
      expect(component.matchesFilter(task, "active")).toBe(true);
      expect(component.matchesFilter({ ...task, active: false }, "inactive")).toBe(true);
    });

    it("returns false when no field matches", () => {
      expect(component.matchesFilter(task, "no-such-thing")).toBe(false);
    });
  });

  it("toggleDetailedView flips the detailedView signal", () => {
    expect(component.detailedView()).toBe(false);
    component.toggleDetailedView();
    expect(component.detailedView()).toBe(true);
    component.toggleDetailedView();
    expect(component.detailedView()).toBe(false);
  });

  describe("formatOptions", () => {
    it("returns an empty string for nullish or non-object input", () => {
      expect(component.formatOptions(null)).toBe("");
      expect(component.formatOptions(undefined)).toBe("");
    });

    it("returns an empty string for an empty options object", () => {
      expect(component.formatOptions({})).toBe("");
    });

    it("lists boolean-flag options by key only, with no value", () => {
      expect(component.formatOptions({ total_tokens: "true", hardware_tokens: "true" }))
        .toBe("total_tokens, hardware_tokens");
    });

    it("renders non-boolean options as 'key: value' and mixes with flag keys", () => {
      expect(component.formatOptions({ total_tokens: "true", event_counter: "foo" }))
        .toBe("total_tokens, event_counter: foo");
    });
  });

  describe("isBooleanValue", () => {
    it("treats 'true' / 'false' (case-insensitive) as boolean", () => {
      expect(component.isBooleanValue("true")).toBe(true);
      expect(component.isBooleanValue("FALSE")).toBe(true);
      expect(component.isBooleanValue(true)).toBe(true);
      expect(component.isBooleanValue(false)).toBe(true);
    });

    it("treats other strings and numbers as non-boolean", () => {
      expect(component.isBooleanValue("foo")).toBe(false);
      expect(component.isBooleanValue("")).toBe(false);
      expect(component.isBooleanValue(0)).toBe(false);
    });
  });

  describe("Selection", () => {
    it("updateSelection adds the task id when the checkbox is checked", () => {
      const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, id: 5 };
      component.updateSelection({ checked: true } as MatCheckboxChange, task);
      expect(component.selectedTaskIds().has(5)).toBe(true);
    });

    it("updateSelection removes the task id when the checkbox is unchecked", () => {
      const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, id: 5 };
      component.selectedTaskIds.set(new Set([5]));
      component.updateSelection({ checked: false } as MatCheckboxChange, task);
      expect(component.selectedTaskIds().has(5)).toBe(false);
    });

    it("updateSelection is a no-op when the task has no id", () => {
      const task: PeriodicTask = { ...EMPTY_PERIODIC_TASK, id: null };
      component.updateSelection({ checked: true } as MatCheckboxChange, task);
      expect(component.selectedTaskIds().size).toBe(0);
    });

    it("isAllSelected is false when nothing is selected", () => {
      periodicTaskService.setPeriodicTasks([
        { ...EMPTY_PERIODIC_TASK, id: 1, name: "a" },
        { ...EMPTY_PERIODIC_TASK, id: 2, name: "b" }
      ]);
      expect(component.isAllSelected()).toBe(false);
    });

    it("isAllSelected is true when every selectable task is selected", () => {
      periodicTaskService.setPeriodicTasks([
        { ...EMPTY_PERIODIC_TASK, id: 1, name: "a" },
        { ...EMPTY_PERIODIC_TASK, id: 2, name: "b" }
      ]);
      component.selectedTaskIds.set(new Set([1, 2]));
      expect(component.isAllSelected()).toBe(true);
    });

    it("masterToggle selects all when nothing is selected", () => {
      periodicTaskService.setPeriodicTasks([
        { ...EMPTY_PERIODIC_TASK, id: 1, name: "a" },
        { ...EMPTY_PERIODIC_TASK, id: 2, name: "b" }
      ]);
      component.masterToggle();
      expect(component.selectedTaskIds()).toEqual(new Set([1, 2]));
    });

    it("masterToggle clears the selection when everything is selected", () => {
      periodicTaskService.setPeriodicTasks([
        { ...EMPTY_PERIODIC_TASK, id: 1, name: "a" },
        { ...EMPTY_PERIODIC_TASK, id: 2, name: "b" }
      ]);
      component.selectedTaskIds.set(new Set([1, 2]));
      component.masterToggle();
      expect(component.selectedTaskIds().size).toBe(0);
    });
  });

  describe("deleteSelected", () => {
    it("is a no-op when no tasks are selected", async () => {
      await component.deleteSelected();
      expect(periodicTaskService.deletePeriodicTask).not.toHaveBeenCalled();
    });

    it("aborts when the user cancels the confirmation dialog", async () => {
      periodicTaskService.setPeriodicTasks([{ ...EMPTY_PERIODIC_TASK, id: 1, name: "doomed" }]);
      component.selectedTaskIds.set(new Set([1]));
      (dialogService.openDialog as jest.Mock).mockReturnValueOnce({ afterClosed: () => of(undefined) });
      await component.deleteSelected();
      expect(periodicTaskService.deletePeriodicTask).not.toHaveBeenCalled();
      expect(periodicTaskService.periodicTasksResource.reload).not.toHaveBeenCalled();
    });

    it("deletes every selected task, clears selection, and reloads on confirmation", async () => {
      periodicTaskService.setPeriodicTasks([
        { ...EMPTY_PERIODIC_TASK, id: 1, name: "a" },
        { ...EMPTY_PERIODIC_TASK, id: 2, name: "b" }
      ]);
      component.selectedTaskIds.set(new Set([1, 2]));
      (dialogService.openDialog as jest.Mock).mockReturnValueOnce({ afterClosed: () => of(true) });
      await component.deleteSelected();
      expect(periodicTaskService.deletePeriodicTask).toHaveBeenCalledTimes(2);
      expect(periodicTaskService.deletePeriodicTask).toHaveBeenCalledWith(1);
      expect(periodicTaskService.deletePeriodicTask).toHaveBeenCalledWith(2);
      expect(notificationService.success).toHaveBeenCalledTimes(2);
      expect(component.selectedTaskIds().size).toBe(0);
      expect(periodicTaskService.periodicTasksResource.reload).toHaveBeenCalled();
    });
  });
});