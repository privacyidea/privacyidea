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

import { TestBed } from "@angular/core/testing";
import { EMPTY_PERIODIC_TASK } from "../../../../../services/periodic-task/periodic-task.service";
import { PeriodicTaskReadComponent } from "./periodic-task-read.component";

describe("PeriodicTaskPanelComponent", () => {
  let component: PeriodicTaskReadComponent;
  let fixture: any;
  let task = {
    ...EMPTY_PERIODIC_TASK,
    id: "1",
    name: "Test Task",
    active: true,
    interval: "*/5 * * * *",
    nodes: ["localnode"],
    taskmodule: "SimpleStats",
    retry_if_failed: true,
    ordering: 0
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskReadComponent],
      providers: []
    }).compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskReadComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("task", task);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly identify date values", () => {
    expect(component.isDateValue("2024-06-01")).toBe(true);
    expect(component.isDateValue("no date")).toBe(false);
    expect(component.isDateValue(1717238400000)).toBe(true);
    expect(component.isDateValue(new Date())).toBe(true);
    expect(component.isDateValue({})).toBe(false);
    expect(component.isDateValue(null)).toBe(false);
  });

  it("should correctly identify boolean actions", () => {
    expect(component.isBooleanAction("true")).toBe(true);
    expect(component.isBooleanAction("false")).toBe(true);
    expect(component.isBooleanAction("TRUE")).toBe(true);
    expect(component.isBooleanAction("False")).toBe(true);
    expect(component.isBooleanAction("yes")).toBe(false);
    expect(component.isBooleanAction("no")).toBe(false);
    expect(component.isBooleanAction("")).toBe(false);
  });

  it("should render interval, nodes, ordering, and retry_if_failed", () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain("Interval " + task.interval );
    expect(compiled.textContent).toContain("Nodes " + task.nodes[0]);
    expect(compiled.textContent).toContain("Ordering " + task.ordering.toString());
    expect(compiled.textContent).toContain("Retry If Failed");
  });

  it("should render options", () => {
    fixture.componentRef.setInput("task", { ...task, options: { event_counter: "test-counter", reset_event_counter: "true" } });
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain("Options");
    expect(compiled.textContent).toContain("event_counter");
    expect(compiled.textContent).toContain("test-counter");
    expect(compiled.textContent).toContain("reset_event_counter");
    expect(compiled.textContent).not.toContain("true");
  });

  it("should render last_runs as dates and fallback", () => {
    fixture.componentRef.setInput("task", {
      ...task, last_runs: {
        node1: "2024-08-03T12:00:00Z",
        node2: 1717238400000,
        node3: "not-a-date"
      }
    });
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const htmlText = compiled.textContent || "";
    expect(htmlText).toContain("node1:  2024-08-03 ");
    expect(htmlText).toContain("node2:  2024-06-01 ");
    expect(htmlText).toContain("node3:  not-a-date");
  });
});