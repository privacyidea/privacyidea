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

import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { Sort } from "@angular/material/sort";
import { provideRouter, Router } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { EventHandler, EventService } from "@services/event/event.service";
import { NotificationService } from "@services/notification/notification.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockDialogService,
  MockNotificationService,
  MockPiResponse,
  MockTableUtilsService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { of } from "rxjs";
import { EventComponent } from "./event.component";

describe("EventComponent", () => {
  let component: EventComponent;
  let fixture: ComponentFixture<EventComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        provideHttpClient(),
        provideRouter([]),
        { provide: EventService, useClass: MockEventService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "eventhandling_read"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should format conditions as string", () => {
    expect(component.formatConditions({ foo: "bar", baz: 42 })).toBe("foo: bar, baz: 42");
    expect(component.formatConditions({})).toBe("");
    expect(component.formatConditions(null)).toBe("");
    expect(component.formatConditions(undefined)).toBe("");
    expect(component.formatConditions("not-an-object")).toBe("");
  });

  it("should return event array if input is array, else empty array", () => {
    expect(component.getEventArray(["a", "b"])).toEqual(["a", "b"]);
    expect(component.getEventArray("not-an-array")).toEqual([]);
    expect(component.getEventArray(null)).toEqual([]);
    expect(component.getEventArray(undefined)).toEqual([]);
  });

  it("should toggle detailedView", () => {
    const initial = component.detailedView();
    component.toggleDetailedView();
    expect(component.detailedView()).toBe(!initial);
    component.toggleDetailedView();
    expect(component.detailedView()).toBe(initial);
  });

  it("should clear filter and call onFilterInput", () => {
    const spy = jest.spyOn(component, "onFilterInput");
    component.filterString.set("something");
    component.onClearFilter();
    expect(component.filterString()).toBe("");
    expect(spy).toHaveBeenCalledWith("");
  });

  it("should set filterString and update eventHandlerDataSource filter", () => {
    const ds = component.eventHandlerDataSource();
    component.onFilterInput("test");
    expect(component.filterString()).toBe("test");
    expect(ds.filter).toBe("test");
  });

  it("onEditEventHandler should navigate to edit event handler route", () => {
    const router = TestBed.inject(Router);
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    const handler = {
      id: 1,
      name: "foo",
      event: [],
      handlermodule: "",
      position: "",
      action: "",
      conditions: {},
      options: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    component.onEditEventHandler(handler);
    expect(spy).toHaveBeenCalled();
  });

  it("should navigate to create new event handler route", () => {
    const router = TestBed.inject(Router);
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.onCreateNewEventHandler();
    expect(spy).toHaveBeenCalled();
  });

  it("should call eventService.deleteWithConfirmDialog on delete", () => {
    const spy = jest.spyOn(component["eventService"], "deleteWithConfirmDialog");
    const handler: EventHandler = {
      id: null,
      name: "foo",
      event: [],
      handlermodule: "",
      position: "",
      action: "",
      conditions: {},
      options: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    component.onDeleteEventHandler(handler);
    expect(spy).toHaveBeenCalled();
  });

  it("should filter eventHandlerDataSource by name", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "SpecialName",
      handlermodule: "mod",
      position: "pos",
      action: "act",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "specialname")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by handlermodule", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "ModuleX",
      position: "p",
      action: "a",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "modulex")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by position", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "m",
      position: "PosY",
      action: "a",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "posy")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by action", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "ActionZ",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "actionz")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by options", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: { foo: "BarOpt" },
      event: [],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "foo: baropt")).toBe(true);
    expect(ds.filterPredicate(handler, "foo")).toBe(true);
    expect(ds.filterPredicate(handler, "baropt")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by events", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: {},
      event: ["EventA"],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "eventa")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by conditions", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: {},
      event: [],
      conditions: { cond: "CondVal" },
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "cond: condval")).toBe(true);
    expect(ds.filterPredicate(handler, "cond")).toBe(true);
    expect(ds.filterPredicate(handler, "condval")).toBe(true);
    expect(ds.filterPredicate(handler, "notfound")).toBe(false);
  });

  it("should return true for empty filter in filterPredicate", () => {
    const ds = component.eventHandlerDataSource();
    const handler: EventHandler = {
      id: null,
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1,
      abort_on_error: false
    };
    expect(ds.filterPredicate(handler, "")).toBe(true);
    expect(ds.filterPredicate(handler, "   ")).toBe(true);
  });

  it("should update totalLength when eventHandlers changes", () => {
    // Simulate eventHandlers signal update
    const eventHandlers: EventHandler[] = [
      {
        id: 1,
        name: "a",
        event: [],
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        conditions: {},
        active: true,
        ordering: 1,
        abort_on_error: false
      },
      {
        id: 2,
        name: "b",
        event: [],
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        conditions: {},
        active: true,
        ordering: 2,
        abort_on_error: false
      }
    ];
    mockEventService.eventHandlers.set(eventHandlers);
    expect(component.totalLength()).toBe(2);
    mockEventService.eventHandlers.set([]);
    expect(component.totalLength()).toBe(0);
  });

  it("should return previous value for totalLength if eventHandlers is null/undefined", () => {
    const eventHandlers: EventHandler[] = [
      {
        id: 1,
        name: "a",
        event: [],
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        conditions: {},
        active: true,
        ordering: 1,
        abort_on_error: false
      }
    ];
    mockEventService.eventHandlers.set(eventHandlers);
    expect(component.totalLength()).toBe(1);
    mockEventService.eventHandlers.set(undefined);
    expect(component.totalLength()).toBe(1); // stays at previous value
  });

  it("should sort event handlers by name ascending", () => {
    const data = [
      {
        name: "Charlie",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 3
      },
      {
        name: "Alice",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 1
      },
      {
        name: "Bob",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 2
      }
    ];
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([...data] as unknown as EventHandler[], { active: "name", direction: "asc" });
    expect(sorted.map((e: EventHandler) => e.name)).toEqual(["Alice", "Bob", "Charlie"]);
  });

  it("should sort event handlers by name descending", () => {
    const data = [
      {
        name: "Charlie",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 3
      },
      {
        name: "Alice",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 1
      },
      {
        name: "Bob",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 2
      }
    ];
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([...data] as unknown as EventHandler[], { active: "name", direction: "desc" });
    expect(sorted.map((e: EventHandler) => e.name)).toEqual(["Charlie", "Bob", "Alice"]);
  });

  it("should sort event handlers by ordering ascending", () => {
    const data = [
      {
        name: "Charlie",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 3
      },
      {
        name: "Alice",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 1
      },
      {
        name: "Bob",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 2
      }
    ];
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([...data] as unknown as EventHandler[], { active: "ordering", direction: "asc" });
    expect(sorted.map((e: EventHandler) => e.ordering)).toEqual([1, 2, 3]);
  });

  it("should sort event handlers by ordering descending", () => {
    const data = [
      {
        name: "Charlie",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 3
      },
      {
        name: "Alice",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 1
      },
      {
        name: "Bob",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 2
      }
    ];
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([...data] as unknown as EventHandler[], { active: "ordering", direction: "desc" });
    expect(sorted.map((e: EventHandler) => e.ordering)).toEqual([3, 2, 1]);
  });

  it("should return original array if no direction is set", () => {
    const data = [
      {
        name: "Charlie",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 3
      },
      {
        name: "Alice",
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        event: [],
        conditions: {},
        active: true,
        ordering: 1
      }
    ];
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([...data] as unknown as EventHandler[], { active: "name", direction: "" });
    expect(sorted).toEqual(data);
  });

  it("should handle empty array", () => {
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([], { active: "name", direction: "asc" });
    expect(sorted).toEqual([]);
  });

  it("should handle missing sort key gracefully", () => {
    const data = [
      { name: "Charlie", ordering: 3 },
      { name: "Alice" },
      { name: "Bob", ordering: 2 }
    ] as unknown as EventHandler[];
    const sorted = (
      component as unknown as { clientsideSortEventData: (data: EventHandler[], s: Sort) => EventHandler[] }
    ).clientsideSortEventData([...data] as unknown as EventHandler[], { active: "ordering", direction: "asc" });
    expect(sorted.map((e: EventHandler) => e.ordering)).toEqual([undefined, 2, 3]);
  });

  it("should call eventService.disableEvent if eventHandler is active", () => {
    const handler = {
      id: "123",
      name: "Test",
      event: [],
      handlermodule: "",
      position: "",
      action: "",
      options: {},
      conditions: {},
      active: true,
      ordering: 1
    };
    const spy = jest.spyOn(component["eventService"], "disableEvent");
    component.toggleActive(handler as unknown as EventHandler);
    expect(spy).toHaveBeenCalledWith("123");
  });

  it("should call eventService.enableEvent if eventHandler is inactive", () => {
    const handler = {
      id: "456",
      name: "Test",
      event: [],
      handlermodule: "",
      position: "",
      action: "",
      options: {},
      conditions: {},
      active: false,
      ordering: 1
    };
    const spy = jest.spyOn(component["eventService"], "enableEvent");
    component.toggleActive(handler as unknown as EventHandler);
    expect(spy).toHaveBeenCalledWith("456");
  });

  describe("ordering in the list view", () => {
    const makeHandler = (
      id: number,
      name: string,
      ordering: number,
      overrides: Partial<EventHandler> = {}
    ): EventHandler => ({
      id,
      name,
      active: true,
      handlermodule: "UserNotification",
      ordering,
      position: "post",
      abort_on_error: false,
      event: ["token_init"],
      action: "sendmail",
      options: {},
      conditions: {},
      ...overrides
    });
    const inputWith = (value: string): HTMLInputElement => {
      const input = document.createElement("input");
      input.value = value;
      return input;
    };
    const grantRights = (rights: string[]) => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
      fixture.detectChanges();
    };
    let notificationService: MockNotificationService;
    let dialogService: MockDialogService;
    let first: EventHandler;

    beforeEach(() => {
      notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      first = makeHandler(1, "first", 1);
      mockEventService.eventHandlers.set([first, makeHandler(2, "second", 2)]);
      fixture.detectChanges();
    });

    it("saves a free ordering without asking", () => {
      component.commitOrdering(first, inputWith("5"));

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(mockEventService.updateOrderings).toHaveBeenCalledWith([{ handler: first, ordering: 5 }]);
      expect(notificationService.success).toHaveBeenCalledWith("Updated the ordering of first.");
    });

    describe("an ordering that is taken", () => {
      let dialogRef: MockMatDialogRef<unknown, boolean>;

      beforeEach(() => {
        dialogRef = new MockMatDialogRef<unknown, boolean>();
        dialogService.openDialog.mockReturnValue(dialogRef);
      });

      it("names the handlers that move up, before anything is saved", () => {
        component.commitOrdering(first, inputWith("2"));

        expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
        expect(mockEventService.updateOrderings).not.toHaveBeenCalled();

        const data = dialogService.openDialog.mock.calls[0][0].data;
        expect(data.title).toBe("Ordering Already Used");
        expect(data.message).toBe(
          "The ordering 2 is already used. These event handlers move up by one to make room: second."
        );
        expect(data.confirmAction.label).toBe("Save");
      });

      it("names every handler of a longer chain and saves them all", () => {
        // 1, 2, 3 in a row: moving the last one onto 1 has to push both others up.
        const middle = makeHandler(2, "second", 2);
        const top = makeHandler(3, "third", 3);
        mockEventService.eventHandlers.set([first, middle, top]);

        component.commitOrdering(top, inputWith("1"));

        expect(dialogService.openDialog.mock.calls[0][0].data.message).toBe(
          "The ordering 1 is already used. These event handlers move up by one to make room: first, second."
        );

        dialogRef.close(true);

        expect(mockEventService.updateOrderings).toHaveBeenCalledWith([
          { handler: top, ordering: 1 },
          { handler: first, ordering: 2 },
          { handler: middle, ordering: 3 }
        ]);
      });

      it("saves the whole chain once the user confirms", () => {
        component.commitOrdering(first, inputWith("2"));
        dialogRef.close(true);

        expect(mockEventService.updateOrderings).toHaveBeenCalledWith([
          { handler: first, ordering: 2 },
          { handler: expect.objectContaining({ name: "second" }), ordering: 3 }
        ]);
        expect(notificationService.success).toHaveBeenCalledWith("Updated the ordering of first.");
      });

      it("restores the previous ordering when the user cancels", () => {
        const input = inputWith("2");

        component.commitOrdering(first, input);
        dialogRef.close(undefined);

        expect(mockEventService.updateOrderings).not.toHaveBeenCalled();
        expect(input.value).toBe("1");
        expect(notificationService.info).toHaveBeenCalledWith("The ordering of first was left unchanged.");
      });
    });

    it("reloads the list after saving", () => {
      const reload = jest.spyOn(mockEventService.allEventsResource, "reload");

      component.commitOrdering(first, inputWith("5"));

      expect(reload).toHaveBeenCalled();
    });

    it("reports nothing as saved when the backend rejects the update", () => {
      mockEventService.updateOrderings.mockReturnValueOnce(of([undefined]));

      component.commitOrdering(first, inputWith("5"));

      expect(notificationService.success).not.toHaveBeenCalled();
      expect(notificationService.warning).not.toHaveBeenCalled();
    });

    it("warns when only part of the chain was saved", () => {
      mockEventService.updateOrderings.mockReturnValueOnce(of([MockPiResponse.fromValue<number>(1), undefined]));

      component.commitOrdering(first, inputWith("5"));

      expect(notificationService.success).not.toHaveBeenCalled();
      expect(notificationService.warning).toHaveBeenCalledWith(
        "Only part of the new ordering was saved. Please check the orderings of the event handlers."
      );
    });

    it.each([
      ["a negative number", "-1"],
      ["a fraction", "1.5"],
      ["an empty field", "   "],
      ["text", "abc"]
    ])("rejects %s and restores the previous ordering", (_label, typed) => {
      const input = inputWith(typed);

      component.commitOrdering(first, input);

      expect(mockEventService.updateOrderings).not.toHaveBeenCalled();
      expect(input.value).toBe("1");
      expect(notificationService.warning).toHaveBeenCalledWith("The ordering has to be a whole number, 0 or higher.");
    });

    it("saves nothing when the ordering did not change", () => {
      component.commitOrdering(first, inputWith("1"));

      expect(mockEventService.updateOrderings).not.toHaveBeenCalled();
      expect(notificationService.warning).not.toHaveBeenCalled();
    });

    it("accepts zero as an ordering", () => {
      component.commitOrdering(first, inputWith("0"));

      expect(mockEventService.updateOrderings).toHaveBeenCalledWith([{ handler: first, ordering: 0 }]);
    });

    it("sorts the ordering by number, not as text", () => {
      mockEventService.eventHandlers.set([
        makeHandler(1, "ten", 10),
        makeHandler(2, "two", 2),
        makeHandler(3, "one", 1)
      ]);
      component.sort.set({ active: "ordering", direction: "asc" });

      expect(component.eventHandlerDataSource().data.map((handler) => handler.ordering)).toEqual([1, 2, 10]);

      component.sort.set({ active: "ordering", direction: "desc" });

      expect(component.eventHandlerDataSource().data.map((handler) => handler.ordering)).toEqual([10, 2, 1]);
    });

    it("renders plain numbers with an edit button, not input fields", () => {
      grantRights(["eventhandling_read", "eventhandling_write"]);

      expect(fixture.nativeElement.querySelector('input[type="number"]')).toBeNull();
      expect(fixture.nativeElement.querySelectorAll(".ordering-edit-button").length).toBe(2);
    });

    it("swaps the number for an input field once editing starts", () => {
      grantRights(["eventhandling_read", "eventhandling_write"]);

      component.startOrderingEdit(first);
      fixture.detectChanges();

      const inputs = fixture.nativeElement.querySelectorAll('input[type="number"]') as NodeListOf<HTMLInputElement>;
      expect(inputs.length).toBe(1);
      expect(inputs[0].value).toBe("1");
      // The other row keeps its pencil, so only one field is open at a time.
      expect(fixture.nativeElement.querySelectorAll(".ordering-edit-button").length).toBe(1);
    });

    it("returns to the plain number when editing is discarded", () => {
      grantRights(["eventhandling_read", "eventhandling_write"]);
      component.startOrderingEdit(first);
      fixture.detectChanges();

      component.cancelOrderingEdit();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('input[type="number"]')).toBeNull();
      expect(mockEventService.updateOrderings).not.toHaveBeenCalled();
    });

    it("closes the field after saving", () => {
      component.startOrderingEdit(first);

      component.commitOrdering(first, inputWith("5"));

      expect(component.editedOrderingId()).toBeNull();
    });

    it("keeps the field open when the typed ordering is unusable", () => {
      component.startOrderingEdit(first);

      component.commitOrdering(first, inputWith("-1"));

      expect(component.editedOrderingId()).toBe(first.id);
    });

    it("closes the field when the ordering was not changed at all", () => {
      component.startOrderingEdit(first);

      component.commitOrdering(first, inputWith("1"));

      expect(component.editedOrderingId()).toBeNull();
      expect(mockEventService.updateOrderings).not.toHaveBeenCalled();
    });

    describe("driven through the rendered cell", () => {
      const editButton = (): HTMLButtonElement => fixture.nativeElement.querySelector(".ordering-edit-button");
      const orderingInput = (): HTMLInputElement => fixture.nativeElement.querySelector('input[aria-label="Ordering"]');
      const buttonLabelled = (label: string): HTMLButtonElement =>
        fixture.nativeElement.querySelector(`button[aria-label="${label}"]`);

      beforeEach(() => {
        grantRights(["eventhandling_read", "eventhandling_write"]);
      });

      it("opens the field when the pencil is clicked", () => {
        editButton().click();
        fixture.detectChanges();

        expect(orderingInput()).not.toBeNull();
        expect(component.editedOrderingId()).toBe(first.id);
      });

      it("saves when the save button is clicked", () => {
        editButton().click();
        fixture.detectChanges();
        orderingInput().value = "5";

        buttonLabelled("Save Ordering").click();

        expect(mockEventService.updateOrderings).toHaveBeenCalledWith([{ handler: first, ordering: 5 }]);
      });

      it("discards when the discard button is clicked", () => {
        editButton().click();
        fixture.detectChanges();
        orderingInput().value = "5";

        buttonLabelled("Discard").click();
        fixture.detectChanges();

        expect(mockEventService.updateOrderings).not.toHaveBeenCalled();
        expect(orderingInput()).toBeNull();
      });

      it("puts the cursor in the field, so the number can be typed straight away", async () => {
        editButton().click();
        fixture.detectChanges();
        await fixture.whenStable();

        expect(document.activeElement).toBe(orderingInput());
      });

      it("moves the open field when the pencil of another row is clicked", () => {
        editButton().click();
        fixture.detectChanges();
        expect(component.editedOrderingId()).toBe(1);

        // Only the still-closed row has a pencil left.
        editButton().click();
        fixture.detectChanges();

        expect(component.editedOrderingId()).toBe(2);
        expect(fixture.nativeElement.querySelectorAll('input[aria-label="Ordering"]').length).toBe(1);
      });

      it("saves on Enter and discards on Escape", () => {
        editButton().click();
        fixture.detectChanges();
        orderingInput().value = "5";

        orderingInput().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        expect(mockEventService.updateOrderings).toHaveBeenCalledWith([{ handler: first, ordering: 5 }]);

        fixture.detectChanges();
        editButton().click();
        fixture.detectChanges();
        orderingInput().dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        fixture.detectChanges();

        expect(orderingInput()).toBeNull();
        expect(mockEventService.updateOrderings).toHaveBeenCalledTimes(1);
      });
    });

    it("keeps the field open when a conflict dialog is cancelled, so the value can be corrected", () => {
      const dialogRef = new MockMatDialogRef<unknown, boolean>();
      dialogService.openDialog.mockReturnValue(dialogRef);
      component.startOrderingEdit(first);

      component.commitOrdering(first, inputWith("2"));
      dialogRef.close(undefined);

      expect(component.editedOrderingId()).toBe(first.id);
    });

    it("renders neither an input nor an edit button for read-only admins", () => {
      grantRights(["eventhandling_read"]);

      expect(fixture.nativeElement.querySelector('input[type="number"]')).toBeNull();
      expect(fixture.nativeElement.querySelector(".ordering-edit-button")).toBeNull();
      expect(fixture.nativeElement.textContent).toContain("first");
    });
  });
});
