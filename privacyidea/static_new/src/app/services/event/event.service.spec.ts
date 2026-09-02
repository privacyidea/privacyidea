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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockDialogService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of, Subject } from "rxjs";
import {
  EventHandler,
  EventHandlerSaveParams,
  EventService,
  planOrderingInsert,
  toEventHandlerSaveParams
} from "./event.service";

describe("EventService", () => {
  let service: EventService;
  let httpMock: HttpTestingController;
  let authServiceMock: MockAuthService;
  let contentServiceMock: MockContentService;
  let notificationMock: MockNotificationService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        EventService,
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    });
    service = TestBed.inject(EventService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    contentServiceMock.routeUrl.set(ROUTE_PATHS.EVENTS);
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.actionAllowed.mockReturnValue(true);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);

    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should save an event handler", () => {
    const event: EventHandlerSaveParams = {
      name: "test",
      handlermodule: "mod",
      active: true,
      ordering: 0,
      abort_on_error: false,
      position: "post",
      event: [],
      action: "",
      conditions: {}
    };
    service.saveEventHandler(event).subscribe((response) => {
      expect(response).toBeTruthy();
      expect(response?.result).toBeDefined();
    });
    const req = httpMock.expectOne(service.eventBaseUrl);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: 1 } });
  });

  it("should handle error when saving an event handler", () => {
    const event: EventHandlerSaveParams = {
      name: "fail",
      handlermodule: "mod",
      active: true,
      ordering: 0,
      abort_on_error: false,
      position: "post",
      event: [],
      action: "",
      conditions: {}
    };
    service.saveEventHandler(event).subscribe((response) => {
      expect(response).toBeUndefined();
      expect(notificationMock.error).toHaveBeenCalledWith(expect.stringContaining("Failed to save event handler."));
    });
    const req = httpMock.expectOne(service.eventBaseUrl);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { error: { message: "Test error" } } }, { status: 400, statusText: "Bad Request" });
  });

  it("should enable an event handler", async () => {
    const eventId = 123;
    const promise = service.enableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/enable/" + encodeURIComponent(eventId));
    expect(req.request.method).toBe("POST");
    req.flush({});
    await expect(promise).resolves.toBeDefined();
  });

  it("should handle error when enabling an event handler", async () => {
    service.allEventsResource.reload = jest.fn();
    const eventId = 123;
    const promise = service.enableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/enable/" + encodeURIComponent(eventId));
    expect(req.request.method).toBe("POST");
    req.flush({}, { status: 500, statusText: "Server Error" });
    await expect(promise).resolves.toBeUndefined();
    expect(notificationMock.error).toHaveBeenCalledWith(expect.stringContaining("Failed to enable event handler!"));
    expect(service.allEventsResource.reload).toHaveBeenCalled();
  });

  it("should disable an event handler", async () => {
    const eventId = 123;
    const promise = service.disableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/disable/" + encodeURIComponent(eventId));
    expect(req.request.method).toBe("POST");
    req.flush({});
    await expect(promise).resolves.toBeDefined();
  });

  it("should handle error when disabling an event handler", async () => {
    const eventId = 456;
    const promise = service.disableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/disable/" + encodeURIComponent(eventId));
    expect(req.request.method).toBe("POST");
    req.flush({}, { status: 500, statusText: "Server Error" });
    await expect(promise).resolves.toBeUndefined();
    expect(notificationMock.error).toHaveBeenCalledWith(expect.stringContaining("Failed to disable event handler!"));
  });

  it("should delete an event handler", () => {
    const eventId = 123;
    service.deleteEvent(eventId).subscribe((response) => {
      expect(response).toBeTruthy();
      expect(response.result).toBeDefined();
    });
    const req = httpMock.expectOne(service.eventBaseUrl + "/" + encodeURIComponent(eventId));
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { value: 1 } });
  });

  it("should handle error when deleting an event handler", (done) => {
    const eventId = 789;
    service.deleteEvent(eventId).subscribe({
      next: () => {
        // Should not be called
        fail("Expected error, but got success response");
      },
      error: () => {
        expect(notificationMock.error).toHaveBeenCalledWith(expect.stringContaining("Failed to delete event handler."));
        done();
      }
    });
    const req = httpMock.expectOne(service.eventBaseUrl + "/" + encodeURIComponent(eventId));
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { error: { message: "Delete error" } } }, { status: 500, statusText: "Server Error" });
  });

  describe("deleteWithConfirmDialog", () => {
    let event: EventHandler;

    beforeEach(() => {
      event = { id: 1, name: "Test Event" } as unknown as EventHandler;
    });

    it("should open confirmation dialog and call delete on success", async () => {
      const response = MockPiResponse.fromValue<number>(event.id as number);
      const deleteSpy = jest.spyOn(service, "deleteEvent").mockReturnValue(of(response));
      const deletePromise = service.deleteWithConfirmDialog(event);

      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
      confirmClosed.next(true);
      confirmClosed.complete();
      await expect(deletePromise).resolves.toEqual(response);

      expect(deleteSpy).toHaveBeenCalledWith(event.id);
      expect(notificationMock.success).toHaveBeenCalledWith("Successfully deleted event handler.");
    });

    it("should open confirmation dialog and do nothing on cancel", async () => {
      const deleteSpy = jest.spyOn(service, "deleteEvent");

      const deletePromise = service.deleteWithConfirmDialog(event);
      confirmClosed.next(false);
      confirmClosed.complete();
      await expect(deletePromise).resolves.toBeUndefined();

      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
      expect(deleteSpy).not.toHaveBeenCalled();
      expect(notificationMock.warning).not.toHaveBeenCalled();
    });
  });

  describe("resources and related signals", () => {
    beforeEach(() => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      contentServiceMock.routeUrl.set(ROUTE_PATHS.EVENTS);
    });

    it("should fetch all events if on the events route and has permission", async () => {
      // Setup
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/`);
      const eventHandlers = [
        {
          id: 1,
          name: "test",
          active: true,
          handlermodule: "testModule",
          ordering: 0,
          position: "post",
          event: ["auth"],
          action: "disable_all_tokens",
          options: {},
          conditions: {}
        }
      ];
      req.flush({ result: { value: eventHandlers } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      const value = service.allEventsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(eventHandlers);
      expect(service.eventHandlers()).toEqual(eventHandlers);
    });

    it("should handle http error for allEventsResource", async () => {
      // Setup
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      // Assertion
      expect(service.eventHandlers()).toEqual([]);
    });

    it("should not fetch events if not on the events route", async () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/`);
      expect(service.allEventsResource.value()).toBeUndefined();
      expect(service.eventHandlers()).toEqual([]);
    });

    it("should not fetch events if action not allowed", async () => {
      // Setup
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/`);
      expect(service.allEventsResource.value()).toBeUndefined();
      expect(service.eventHandlers()).toEqual([]);
    });

    it("should load all handler modules", async () => {
      // Setup
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/handlermodules`);
      const handlerModules = ["module1", "module2"];
      req.flush({ result: { value: handlerModules } });
      await Promise.resolve();

      // Assertion
      const value = service.eventHandlerModulesResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(handlerModules);
      expect(service.eventHandlerModules()).toEqual(handlerModules);
    });

    it("eventHandlerModules should return empty list if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/handlermodules`);
      expect(service.eventHandlerModulesResource.value()).toBeUndefined();
      expect(service.eventHandlerModules()).toEqual([]);
    });

    it("eventHandlerModules should return empty list if http error occurs", async () => {
      TestBed.tick();

      const req = httpMock.expectOne(`${service.eventBaseUrl}/handlermodules`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.eventHandlerModules()).toEqual([]);
    });

    it("should load all event", async () => {
      // Setup
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/available`);
      const events = ["event1", "event2"];
      req.flush({ result: { value: events } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      const value = service.availableEventsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(events);
      expect(service.availableEvents()).toEqual(events);
    });

    it("should handle http error for availableEventsResource", async () => {
      TestBed.tick();

      const req = httpMock.expectOne(`${service.eventBaseUrl}/available`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.availableEvents()).toEqual([]);
    });

    it("availableEvents should return empty list if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/available`);
      expect(service.availableEventsResource.value()).toBeUndefined();
      expect(service.availableEvents()).toEqual([]);
    });

    it("should load all module positions if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/positions/testModule`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      // Assertion
      expect(service.modulePositions()).toEqual([]);
    });

    it("should handle http error for modulePositionsResource", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/positions/testModule`);
      const positions = ["pre", "post"];
      req.flush({ result: { value: positions } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      const value = service.modulePositionsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(positions);
      expect(service.modulePositions()).toEqual(positions);
    });

    it("modulePositions should return empty list if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/positions/testModule`);
      expect(service.modulePositionsResource.value()).toBeUndefined();
      expect(service.modulePositions()).toEqual([]);
    });

    it("should load the module defaults if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/defaults/testModule`);
      req.flush({ result: { value: { abort_on_error: true } } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      expect(service.moduleDefaults()).toEqual({ abort_on_error: true });
    });

    it("moduleDefaults should return null if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/defaults/testModule`);
      expect(service.moduleDefaultsResource.value()).toBeUndefined();
      expect(service.moduleDefaults()).toBeNull();
    });

    it("should handle http error for moduleDefaultsResource", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/defaults/testModule`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      // Assertion
      expect(service.moduleDefaults()).toBeNull();
    });

    it("should load all module actions if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/actions/testModule`);
      const actions = [{ action1: { option1: {}, option2: {} } }, { action2: {} }];
      req.flush({ result: { value: actions } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      const value = service.moduleActionsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(actions);
      expect(service.moduleActions()).toEqual(actions);
    });

    it("should handle http error for moduleActionsResource", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/actions/testModule`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      // Assertion
      expect(service.moduleActions()).toEqual({});
    });

    it("moduleActions should return empty dict if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/actions/testModule`);
      expect(service.moduleActionsResource.value()).toBeUndefined();
      expect(service.moduleActions()).toEqual({});
    });

    it("should load all module conditions if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/conditions/testModule`);
      const conditions = { condition1: { desc: "", type: "str" }, condition2: { desc: "", type: "int" } };
      req.flush({ result: { value: conditions } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      const value = service.moduleConditionsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(conditions);
      expect(service.moduleConditions()).toEqual(conditions);
    });

    it("should handle http error for moduleConditionsResource", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/conditions/testModule`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      // Assertion
      expect(service.moduleConditions()).toEqual({});
    });

    it("moduleConditions should return empty list if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.tick();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/actions/testModule`);
      expect(service.moduleConditionsResource.value()).toBeUndefined();
      expect(service.moduleConditions()).toEqual({});
    });

    it("moduleConditionsByGroup should sort conditions by the defined group", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.tick();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/conditions/testModule`);
      const conditions = {
        condition1: { desc: "", type: "str", group: "group1" },
        condition2: { desc: "", type: "int", group: "group2" },
        condition3: { desc: "", type: "str" },
        condition4: { desc: "", type: "str", group: "group1" }
      };
      req.flush({ result: { value: conditions } });
      TestBed.tick();
      await Promise.resolve();

      // Assertion
      const value = service.moduleConditionsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(conditions);
      expect(service.moduleConditions()).toEqual(conditions);
      expect(Object.keys(service.moduleConditionsByGroup())).toEqual(["group1", "group2", "miscellaneous"]);
      expect(service.moduleConditionsByGroup()["group1"]).toEqual({
        condition1: { desc: "", type: "str", group: "group1" },
        condition4: { desc: "", type: "str", group: "group1" }
      });
      expect(service.moduleConditionsByGroup()["group2"]).toEqual({
        condition2: { desc: "", type: "int", group: "group2" }
      });
      expect(service.moduleConditionsByGroup()["miscellaneous"]).toEqual({
        condition3: { desc: "", type: "str" }
      });
    });
  });
  describe("ordering updates", () => {
    const handler: EventHandler = {
      id: 7,
      name: "notify",
      active: true,
      handlermodule: "UserNotification",
      ordering: 3,
      position: "post",
      abort_on_error: false,
      event: ["token_init"],
      action: "sendmail",
      options: { subject: "Hello", emailconfig: "smtp1" },
      conditions: { tokentype: "hotp" }
    };

    it("toEventHandlerSaveParams flattens the options the backend would otherwise drop", () => {
      const params = toEventHandlerSaveParams(handler);

      expect(params["option.subject"]).toBe("Hello");
      expect(params["option.emailconfig"]).toBe("smtp1");
      expect(params).not.toHaveProperty("options");
      expect(params.id).toBe("7");
      expect(params.conditions).toEqual({ tokentype: "hotp" });
      expect(params.action).toBe("sendmail");
      expect(params.position).toBe("post");
    });

    it("toEventHandlerSaveParams omits the id of an unsaved handler", () => {
      expect(toEventHandlerSaveParams({ ...handler, id: null }).id).toBeUndefined();
    });
  });

  describe("planOrderingInsert", () => {
    const handler = (id: number, ordering: number): EventHandler => ({
      id,
      name: `handler-${id}`,
      active: true,
      handlermodule: "UserNotification",
      ordering,
      position: "post",
      abort_on_error: false,
      event: ["token_init"],
      action: "sendmail",
      options: {},
      conditions: {}
    });
    const plan = (handlers: EventHandler[], moved: EventHandler, ordering: number) =>
      planOrderingInsert(handlers, moved, ordering).map((update) => [update.handler.id, update.ordering]);

    it("only moves the edited handler when the ordering is free", () => {
      const list = [handler(1, 1), handler(2, 2), handler(3, 7)];

      expect(plan(list, list[2], 4)).toEqual([[3, 4]]);
    });

    it("pushes the handler that held the ordering up by one", () => {
      const list = [handler(1, 1), handler(2, 2), handler(3, 7)];

      expect(plan(list, list[2], 2)).toEqual([
        [3, 2],
        [2, 3]
      ]);
    });

    it("cascades while the orderings above are taken and stops at the first free one", () => {
      const list = [handler(1, 1), handler(2, 2), handler(3, 3), handler(4, 7)];

      // 7 moves onto 2, which pushes 2 to 3 and 3 to 4. 4 is free, so 1 stays put.
      expect(plan(list, list[3], 2)).toEqual([
        [4, 2],
        [2, 3],
        [3, 4]
      ]);
    });

    it("stops at a gap instead of renumbering everything above it", () => {
      const list = [handler(1, 1), handler(2, 2), handler(3, 4), handler(4, 5)];

      // Moving 5 onto 1 fills the gap at 3, so the handler at 4 keeps its ordering.
      expect(plan(list, list[3], 1)).toEqual([
        [4, 1],
        [1, 2],
        [2, 3]
      ]);
    });

    it("keeps the displaced handlers in their original order", () => {
      const list = [handler(1, 5), handler(2, 6), handler(3, 7), handler(4, 20)];

      expect(plan(list, list[3], 5)).toEqual([
        [4, 5],
        [1, 6],
        [2, 7],
        [3, 8]
      ]);
    });

    it("resolves an ordering that two stored handlers already share", () => {
      const list = [handler(1, 1), handler(2, 5), handler(3, 5)];

      expect(plan(list, list[0], 5)).toEqual([
        [1, 5],
        [2, 6],
        [3, 7]
      ]);
    });

    it("leaves the handlers below the target alone", () => {
      const list = [handler(1, 0), handler(2, 1), handler(3, 2), handler(4, 9)];

      const moved = plan(list, list[3], 1).map(([id]) => id);
      expect(moved).not.toContain(1);
    });

    it("accepts zero as the target ordering", () => {
      const list = [handler(1, 0), handler(2, 1), handler(3, 9)];

      expect(plan(list, list[2], 0)).toEqual([
        [3, 0],
        [1, 1],
        [2, 2]
      ]);
    });
  });

  describe("updateOrderings", () => {
    const handler: EventHandler = {
      id: 7,
      name: "notify",
      active: true,
      handlermodule: "UserNotification",
      ordering: 3,
      position: "post",
      abort_on_error: false,
      event: ["token_init"],
      action: "sendmail",
      options: { subject: "Hello" },
      conditions: {}
    };

    it("posts one handler at a time, starting at the highest ordering", () => {
      const other: EventHandler = { ...handler, id: 8, name: "other", ordering: 5, options: {} };
      const done: unknown[] = [];

      service
        .updateOrderings([
          { handler, ordering: 5 },
          { handler: other, ordering: 6 }
        ])
        .subscribe((responses) => done.push(...responses));

      const first = httpMock.expectOne(service.eventBaseUrl);
      expect(first.request.body).toMatchObject({ id: "8", ordering: 6 });

      httpMock.verify();
      first.flush({ result: { value: 8 } });

      const second = httpMock.expectOne(service.eventBaseUrl);
      expect(second.request.body).toMatchObject({ id: "7", ordering: 5, "option.subject": "Hello" });
      second.flush({ result: { value: 7 } });

      expect(done.length).toBe(2);
    });

    it("does not call the backend without updates", () => {
      let emitted: unknown[] | undefined;
      service.updateOrderings([]).subscribe((result) => (emitted = result));

      httpMock.expectNone(service.eventBaseUrl);
      expect(emitted).toEqual([]);
    });
  });
});
