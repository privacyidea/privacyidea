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
import { EventService } from "./event.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { MockContentService, MockDialogService, MockNotificationService } from "../../../testing/mock-services";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { NotificationService } from "../notification/notification.service";
import { of, Subject } from "rxjs";
import { ROUTE_PATHS } from "../../route_paths";
import { ContentService } from "../content/content.service";
import { AuthService } from "../auth/auth.service";
import { DialogService } from "../dialog/dialog.service";
import { MockMatDialogRef } from "../../../testing/mock-mat-dialog-ref";

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
    const event = { name: "test", handlermodule: "mod" };
    service.saveEventHandler(event).subscribe((response) => {
      expect(response).toBeTruthy();
      expect(response?.result).toBeDefined();
    });
    const req = httpMock.expectOne(service.eventBaseUrl);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { value: 1 } });
  });

  it("should handle error when saving an event handler", () => {
    const event = { name: "fail", handlermodule: "mod" };
    service.saveEventHandler(event).subscribe((response) => {
      expect(response).toBeUndefined();
      expect(notificationMock.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining("Failed to save event handler.")
      );
    });
    const req = httpMock.expectOne(service.eventBaseUrl);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { error: { message: "Test error" } } }, { status: 400, statusText: "Bad Request" });
  });

  it("should enable an event handler", async () => {
    const eventId = "123";
    const promise = service.enableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/enable/" + eventId);
    expect(req.request.method).toBe("POST");
    req.flush({});
    await expect(promise).resolves.toBeDefined();
  });

  it("should handle error when enabling an event handler", async () => {
    service.allEventsResource.reload = jest.fn();
    const eventId = "err123";
    const promise = service.enableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/enable/" + eventId);
    expect(req.request.method).toBe("POST");
    req.flush({}, { status: 500, statusText: "Server Error" });
    await expect(promise).resolves.toBeUndefined();
    expect(notificationMock.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Failed to enable event handler!")
    );
    expect(service.allEventsResource.reload).toHaveBeenCalled();
  });

  it("should disable an event handler", async () => {
    const eventId = "123";
    const promise = service.disableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/disable/" + eventId);
    expect(req.request.method).toBe("POST");
    req.flush({});
    await expect(promise).resolves.toBeDefined();
  });

  it("should handle error when disabling an event handler", async () => {
    const eventId = "err456";
    const promise = service.disableEvent(eventId);
    const req = httpMock.expectOne(service.eventBaseUrl + "/disable/" + eventId);
    expect(req.request.method).toBe("POST");
    req.flush({}, { status: 500, statusText: "Server Error" });
    await expect(promise).resolves.toBeUndefined();
    expect(notificationMock.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Failed to disable event handler!")
    );
  });

  it("should delete an event handler", () => {
    const eventId = "123";
    service.deleteEvent(eventId).subscribe((response) => {
      expect(response).toBeTruthy();
      expect(response.result).toBeDefined();
    });
    const req = httpMock.expectOne(service.eventBaseUrl + "/" + eventId);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { value: 1 } });
  });

  it("should handle error when deleting an event handler", (done) => {
    const eventId = "err789";
    service.deleteEvent(eventId).subscribe({
      next: () => {
        // Should not be called
        fail("Expected error, but got success response");
      },
      error: (err) => {
        expect(notificationMock.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining("Failed to delete event handler.")
        );
        done();
      }
    });
    const req = httpMock.expectOne(service.eventBaseUrl + "/" + eventId);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { error: { message: "Delete error" } } }, { status: 500, statusText: "Server Error" });
  });

  describe("deleteWithConfirmDialog", () => {
    let event: any;

    beforeEach(() => {
      event = { id: "1", name: "Test Event" } as any;
    });

    it("should open confirmation dialog and call delete on success", async () => {
      const response = { result: { value: event.id } };
      const deleteSpy = jest.spyOn(service, "deleteEvent").mockReturnValue(of(response as any));
      const deletePromise = service.deleteWithConfirmDialog(event);

      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
      confirmClosed.next(true);
      confirmClosed.complete();
      await expect(deletePromise).resolves.toEqual(response);

      expect(deleteSpy).toHaveBeenCalledWith(event.id);
      expect(notificationMock.openSnackBar).toHaveBeenCalledWith("Successfully deleted event handler.");
    });

    it("should open confirmation dialog and do nothing on cancel", async () => {
      const deleteSpy = jest.spyOn(service, "deleteEvent");

      const deletePromise = service.deleteWithConfirmDialog(event);
      confirmClosed.next(false);
      confirmClosed.complete();
      await expect(deletePromise).resolves.toBeUndefined();

      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
      expect(deleteSpy).not.toHaveBeenCalled();
      expect(notificationMock.openSnackBar).not.toHaveBeenCalled();
    });
  });

  describe("resources and related signals", () => {
    beforeEach(() => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      contentServiceMock.routeUrl.set(ROUTE_PATHS.EVENTS);
    });

    it("should fetch all events if on the events route and has permission", async () => {
      // Setup
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/`);
      const eventHandlers = [
        {
          id: "1",
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
      TestBed.flushEffects();
      await Promise.resolve();

      // Assertion
      const value = service.allEventsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(eventHandlers);
      expect(service.eventHandlers()).toEqual(eventHandlers);
    });

    it("should not fetch events if not on the events route", async () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/`);
      expect(service.allEventsResource.value()).toBeUndefined();
      expect(service.eventHandlers()).toEqual([]);
    });

    it("should not fetch events if action not allowed", async () => {
      // Setup
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/`);
      expect(service.allEventsResource.value()).toBeUndefined();
      expect(service.eventHandlers()).toEqual([]);
    });

    it("should load all handler modules", async () => {
      // Setup
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/handlermodules`);
      const handlerModules = ["module1", "module2"];
      req.flush({ result: { value: handlerModules } });
      TestBed.flushEffects();
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
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/handlermodules`);
      expect(service.eventHandlerModulesResource.value()).toBeUndefined();
      expect(service.eventHandlerModules()).toEqual([]);
    });

    it("should load all event", async () => {
      // Setup
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/available`);
      const events = ["event1", "event2"];
      req.flush({ result: { value: events } });
      TestBed.flushEffects();
      await Promise.resolve();

      // Assertion
      const value = service.availableEventsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(events);
      expect(service.availableEvents()).toEqual(events);
    });

    it("availableEvents should return empty list if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/available`);
      expect(service.availableEventsResource.value()).toBeUndefined();
      expect(service.availableEvents()).toEqual([]);
    });

    it("should load all module positions if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/positions/testModule`);
      const positions = ["pre", "post"];
      req.flush({ result: { value: positions } });
      TestBed.flushEffects();
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
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/positions/testModule`);
      expect(service.modulePositionsResource.value()).toBeUndefined();
      expect(service.modulePositions()).toEqual([]);
    });

    it("should load all module actions if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/actions/testModule`);
      const actions = [{ action1: { option1: {}, option2: {} } }, { action2: {} }];
      req.flush({ result: { value: actions } });
      TestBed.flushEffects();
      await Promise.resolve();

      // Assertion
      const value = service.moduleActionsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(actions);
      expect(service.moduleActions()).toEqual(actions);
    });

    it("moduleActions should return empty dict if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/actions/testModule`);
      expect(service.moduleActionsResource.value()).toBeUndefined();
      expect(service.moduleActions()).toEqual({});
    });

    it("should load all module conditions if handler module is selected", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/conditions/testModule`);
      const conditions = { condition1: { desc: "", type: "str" }, condition2: { desc: "", type: "int" } };
      req.flush({ result: { value: conditions } });
      TestBed.flushEffects();
      await Promise.resolve();

      // Assertion
      const value = service.moduleConditionsResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(conditions);
      expect(service.moduleConditions()).toEqual(conditions);
    });

    it("moduleConditions should return empty list if resource not loaded", () => {
      // Setup
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.eventBaseUrl}/actions/testModule`);
      expect(service.moduleConditionsResource.value()).toBeUndefined();
      expect(service.moduleConditions()).toEqual({});
    });

    it("moduleConditionsByGroup should sort conditions by the defined group", async () => {
      // Setup
      service.selectedHandlerModule.set("testModule");
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.eventBaseUrl}/conditions/testModule`);
      const conditions = {
        condition1: { desc: "", type: "str", group: "group1" },
        condition2: { desc: "", type: "int", group: "group2" },
        condition3: { desc: "", type: "str" },
        condition4: { desc: "", type: "str", group: "group1" }
      };
      req.flush({ result: { value: conditions } });
      TestBed.flushEffects();
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
});
