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
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { EMPTY_PERIODIC_TASK, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { PeriodicTaskComponent } from "./periodic-task.component";

describe("PeriodicTaskComponent", () => {
  let component: PeriodicTaskComponent;
  let fixture: ComponentFixture<PeriodicTaskComponent>;
  let periodicTaskService: PeriodicTaskService;
  let pendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    periodicTaskService = new MockPeriodicTaskService() as any;

    await TestBed.configureTestingModule({
      imports: [PeriodicTaskComponent],
      providers: [
        provideHttpClient(),
        { provide: PeriodicTaskService, useValue: periodicTaskService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskComponent);
    component = fixture.componentInstance;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call fetchAllModuleOptions on ngOnInit", () => {
    const spy = jest.spyOn(periodicTaskService, "fetchAllModuleOptions");
    component.ngOnInit();
    expect(spy).toHaveBeenCalled();
  });

  it("should reset newTask to EMPTY_PERIODIC_TASK", () => {
    component.newTask = { ...EMPTY_PERIODIC_TASK, name: "test" };
    component.resetNewTask();
    expect(component.newTask).toEqual(EMPTY_PERIODIC_TASK);
  });

  it("should initialize periodicTasks signal", () => {
    expect(component.periodicTasks).toBeDefined();
  });

  it("ngOnDestroy clears all pending-changes registrations", () => {
    component.ngOnDestroy();
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });
});
