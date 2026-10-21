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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { EMPTY_EVENT, EventHandler, EventService, MAX_ORDERING } from "@services/event/event.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  MockAuthService,
  MockNotificationService,
  MockPendingChangesService,
  MockRouter
} from "@testing/mock-services";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { BehaviorSubject, of, throwError } from "rxjs";
import { EventEditPageComponent } from "./event-edit-page.component";

globalThis.IntersectionObserver = class IntersectionObserver {
  disconnect = jest.fn();
  observe = jest.fn();
  unobserve = jest.fn();
  takeRecords = (): IntersectionObserverEntry[] => [];
} as unknown as typeof IntersectionObserver;

const mockEventHandler: EventHandler = {
  id: 1,
  name: "TestHandler",
  handlermodule: "mockModule",
  active: true,
  event: ["eventA", "eventB"],
  action: "actionB",
  options: { opt3: "true" },
  conditions: { condA: "true" },
  position: "post",
  ordering: 0,
  abort_on_error: false
};

const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((error) => error.kind);

describe("EventEditPageComponent — edit mode", () => {
  let component: EventEditPageComponent;
  let fixture: ComponentFixture<EventEditPageComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;
  let mockRouter: MockRouter;
  let mockPendingChangesService: MockPendingChangesService;
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;

  beforeEach(async () => {
    paramMap$ = new BehaviorSubject(convertToParamMap({ id: String(mockEventHandler.id) }));

    await TestBed.configureTestingModule({
      imports: [EventEditPageComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: Router, useClass: MockRouter },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: paramMap$.asObservable(),
            snapshot: { paramMap: convertToParamMap({ id: String(mockEventHandler.id) }) }
          }
        }
      ]
    }).compileComponents();

    // Inject services and set up data BEFORE creating the component
    // so the constructor's paramMap subscription finds the handler immediately
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockRouter = TestBed.inject(Router) as unknown as MockRouter;
    mockPendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    mockEventService.eventHandlers.set([mockEventHandler]);
    mockEventService.selectedHandlerModule.set(mockEventHandler.handlermodule);

    fixture = TestBed.createComponent(EventEditPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize editEvent from the event handlers list and set selected handler module", () => {
    expect(component.editEvent().id).toBe(mockEventHandler.id);
    expect(component.editEvent().name).toBe("TestHandler");
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
  });

  it("should set isNewEvent to false in edit mode", () => {
    expect(component.isNewEvent()).toBe(false);
  });

  it("should show 'Edit Event Handler' as title", () => {
    expect(component.title()).toEqual("Edit Event Handler");
  });

  it("should set new action using setNewAction", () => {
    component.setNewAction("actionC");
    expect(component.editEvent().action).toBe("actionC");
  });

  it("should set new options using setNewOptions", () => {
    const newOptions = { optX: "valX", optY: 42 };
    component.setNewOptions(newOptions);
    expect(component.editEvent().options).toEqual(newOptions);
  });

  it("should set new conditions using setNewConditions", () => {
    const newConditions = { condX: "true", condY: "false" };
    component.setNewConditions(newConditions);
    expect(component.editEvent().conditions).toEqual(newConditions);
  });

  it("should set new events using setNewEvents", () => {
    const newEvents = ["eventZ", "eventW"];
    component.setNewEvents(newEvents);
    expect(component.editEvent().event).toEqual(newEvents);
  });

  it("should update the edited event handler through the form", () => {
    component.editForm.name().controlValue.set("HandlerUpdated");
    expect(component.editEvent().name).toBe("HandlerUpdated");
    component.editForm.ordering().controlValue.set(99);
    expect(component.editEvent().ordering).toBe(99);
  });

  it("should not touch the shared empty event", () => {
    component.editForm.name().controlValue.set("Changed");
    expect(EMPTY_EVENT.name).toBe("");
    expect(Object.getOwnPropertySymbols(EMPTY_EVENT)).toHaveLength(0);
  });

  describe("validity", () => {
    it("canSave should be true if all rules hold", () => {
      expect(component.editForm().valid()).toBe(true);
      expect(component.validOptions()).toBe(true);
      expect(component.canSave()).toBe(true);
    });

    it("canSave should be false if name is not set", () => {
      component.editEvent.update((handler) => ({ ...handler, name: "" }));
      expect(kinds(component.editForm.name())).toEqual(["required"]);
      expect(component.canSave()).toBe(false);
    });

    it("should reject a name with characters other than alphanumerics, spaces, dots, underscores and hyphens", () => {
      component.editEvent.update((handler) => ({ ...handler, name: "bad/name" }));
      expect(kinds(component.editForm.name())).toEqual(["pattern"]);
      expect(component.canSave()).toBe(false);
      component.editEvent.update((handler) => ({ ...handler, name: "good name-1_a.b" }));
      expect(kinds(component.editForm.name())).toEqual([]);
    });

    it("canSave should be false if position is not set", () => {
      component.editEvent.update((handler) => ({ ...handler, position: "" }));
      expect(kinds(component.editForm.position())).toEqual(["required"]);
      expect(component.canSave()).toBe(false);
    });

    it("canSave should be false if event is not set", () => {
      component.editEvent.update((handler) => ({ ...handler, event: [] }));
      expect(kinds(component.editForm.event())).toEqual(["required"]);
      expect(component.canSave()).toBe(false);
    });

    it("canSave should be false if no action is set", () => {
      component.editEvent.update((handler) => ({ ...handler, action: "" }));
      expect(kinds(component.editForm.action())).toEqual(["required"]);
      expect(component.canSave()).toBe(false);
    });

    it("canSave should be false while the options of the action are invalid", () => {
      component.validOptions.set(false);
      expect(component.editForm().valid()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("should not check the handler module of an existing event handler, which cannot be changed", () => {
      component.editEvent.update((handler) => ({ ...handler, handlermodule: "" }));
      expect(component.editForm.handlermodule().disabled()).toBe(true);
      expect(component.canSave()).toBe(true);
    });

    it("canSave should be false if a condition has no value", () => {
      for (const missing of [null, undefined, ""]) {
        component.editEvent.update((handler) => ({
          ...handler,
          conditions: { cond1: "1", cond2: missing } as unknown as Record<string, string>
        }));
        expect(kinds(component.editForm.conditions())).toEqual(["conditionValue"]);
        expect(component.canSave()).toBe(false);
      }
    });

    it("should accept conditions without a condition, or whose values are all set", () => {
      component.editEvent.update((handler) => ({ ...handler, conditions: {} }));
      expect(kinds(component.editForm.conditions())).toEqual([]);
      component.editEvent.update((handler) => ({
        ...handler,
        conditions: { cond1: "1", cond2: false } as unknown as Record<string, string>
      }));
      expect(kinds(component.editForm.conditions())).toEqual([]);
      component.editEvent.update((handler) => ({
        ...handler,
        conditions: undefined as unknown as Record<string, string>
      }));
      expect(component.editForm().valid()).toBe(true);
    });

    it("should disable the name while the event handler is not loaded", () => {
      expect(component.editForm.name().disabled()).toBe(false);
      component.editEvent.set(EMPTY_EVENT);
      expect(component.eventLoaded()).toBe(false);
      expect(component.editForm.name().disabled()).toBe(true);
    });
  });

  describe("ordering", () => {
    const orderingInput = (): HTMLInputElement => fixture.nativeElement.querySelector('input[type="number"]');
    const type = (value: string) => {
      orderingInput().value = value;
      orderingInput().dispatchEvent(new Event("input"));
      orderingInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
    };
    const errorTexts = (): string =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-error"))
        .map((el) => (el as HTMLElement).textContent)
        .join("|");

    it("should show the ordering of the handler", () => {
      expect(orderingInput().value).toBe("0");
    });

    it("should write a typed number to the model as a number", () => {
      type("7");
      expect(component.editEvent().ordering).toBe(7);
      expect(kinds(component.editForm.ordering())).toEqual([]);
    });

    it("should accept the bounds 0 and the largest ordering the column holds", () => {
      type("0");
      expect(kinds(component.editForm.ordering())).toEqual([]);
      type(String(MAX_ORDERING));
      expect(kinds(component.editForm.ordering())).toEqual([]);
    });

    it("should require an ordering and show the message after the field was left", () => {
      type("");
      expect(kinds(component.editForm.ordering())).toEqual(["required"]);
      expect(component.canSave()).toBe(false);
      expect(errorTexts()).toContain("Ordering is required.");
    });

    it.each([
      ["a negative number", "-1"],
      ["a fraction", "1.5"],
      ["a number the column cannot hold", String(MAX_ORDERING + 1)]
    ])("should reject %s", (_label, typed) => {
      type(typed);
      expect(kinds(component.editForm.ordering())).toEqual(["orderingRange"]);
      expect(component.canSave()).toBe(false);
      expect(errorTexts()).toContain(`Ordering has to be a whole number between 0 and ${MAX_ORDERING}.`);
    });

    it("should report a parse error for input that is no number", () => {
      const validity = jest.spyOn(orderingInput(), "validity", "get");
      validity.mockReturnValue({ badInput: true } as ValidityState);
      type("");
      expect(kinds(component.editForm.ordering())).toEqual(["parse"]);
      expect(component.canSave()).toBe(false);
      expect(errorTexts()).toContain("Ordering has to be a number.");
      validity.mockReturnValue({ badInput: false } as ValidityState);
    });
  });

  describe("form controls", () => {
    const nameInput = (): HTMLInputElement => fixture.nativeElement.querySelector('input[type="text"]');
    const type = (value: string) => {
      nameInput().value = value;
      nameInput().dispatchEvent(new Event("input"));
      fixture.detectChanges();
    };
    const selects = () =>
      fixture.debugElement.queryAll(By.directive(MatSelect)).map((el) => el.componentInstance as MatSelect);
    const errorTexts = (): string =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-error"))
        .map((el) => (el as HTMLElement).textContent)
        .join("|");

    afterEach(() => {
      document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
    });

    it("should show the name, and write typed text to the model and mark the field dirty", () => {
      expect(nameInput().value).toBe("TestHandler");
      expect(component.editForm.name().dirty()).toBe(false);
      type("Typed name");
      expect(component.editEvent().name).toBe("Typed name");
      expect(component.editForm.name().dirty()).toBe(true);
    });

    it("should show the required error of the name after the field was left", () => {
      type("");
      expect(errorTexts()).not.toContain("Name is required.");
      nameInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(errorTexts()).toContain("Name is required.");
    });

    it("should show the pattern error of the name", () => {
      type("bad/name");
      nameInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(errorTexts()).toContain("Name contains invalid characters.");
      expect(errorTexts()).not.toContain("Name is required.");
    });

    it("should clear the name with the clear button", () => {
      component.clearName();
      fixture.detectChanges();
      expect(component.editEvent().name).toBe("");
      expect(nameInput().value).toBe("");
      expect(component.editForm.name().dirty()).toBe(true);
    });

    it("should show the handler module as selected and keep it read-only in edit mode", () => {
      const handlerModule = selects()[0];
      expect(handlerModule.value).toBe("mockModule");
      expect(handlerModule.disabled).toBe(true);
      expect(handlerModule.triggerValue).toBe("mockModule");
    });

    it("should follow the handler module of the edited event handler in the service", () => {
      expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
      component.editEvent.update((handler) => ({ ...handler, handlermodule: "anotherModule" }));
      fixture.detectChanges();
      expect(mockEventService.selectedHandlerModule()).toBe("anotherModule");
    });

    it("should show the position and write the picked position to the model", async () => {
      const position = selects()[1];
      expect(position.value).toBe("post");
      position.open();
      fixture.detectChanges();
      await fixture.whenStable();
      (document.querySelectorAll("mat-option")[0] as HTMLElement).click();
      fixture.detectChanges();
      expect(component.editEvent().position).toBe("pre");
      expect(component.editForm.position().dirty()).toBe(true);
      expect(component.hasChanges()).toBe(true);
    });

    it("should show the required error of the position once it is touched", () => {
      component.editEvent.update((handler) => ({ ...handler, position: "" }));
      component.editForm.position().markAsTouched();
      fixture.detectChanges();
      expect(errorTexts()).toContain("Selecting a position is required.");
    });

    it("should disable the active toggle without the right to write event handlers", () => {
      const toggle = () => fixture.nativeElement.querySelector("mat-slide-toggle button") as HTMLButtonElement;
      expect(component.editForm.active().disabled()).toBe(true);
      expect(toggle().disabled).toBe(true);
    });

    it("should write the active toggle to the model when the right to write event handlers is given", () => {
      const auth = TestBed.inject(AuthService) as unknown as MockAuthService;
      auth.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["eventhandling_write"] });
      fixture.detectChanges();
      const toggle = fixture.nativeElement.querySelector("mat-slide-toggle button") as HTMLButtonElement;
      expect(toggle.disabled).toBe(false);
      toggle.click();
      fixture.detectChanges();
      expect(component.editEvent().active).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-slide-toggle").textContent).toContain("Inactive");
    });

    it("should write the abort on error toggle to the model and send it", () => {
      const toggles = fixture.nativeElement.querySelectorAll("mat-slide-toggle button");
      toggles[1].click();
      fixture.detectChanges();
      expect(component.editEvent().abort_on_error).toBe(true);
      expect(component.getSaveParameters().abort_on_error).toBe(true);
    });

    it("should enable the save button only if the event handler can be saved", () => {
      const save = () => fixture.nativeElement.querySelector("button.action-button-primary") as HTMLButtonElement;
      expect(save().disabled).toBe(false);
      type("");
      expect(save().disabled).toBe(true);
    });
  });

  describe("hasChanges", () => {
    it("should be false after opening, although the action tab reports its options", () => {
      expect(component.hasChanges()).toBe(false);
    });

    it("should be false after opening an event handler whose options lack some options of its action", () => {
      mockEventService.eventHandlers.set([
        { ...mockEventHandler, id: 2, action: "actionA", options: { opt1: "true" } }
      ]);
      paramMap$.next(convertToParamMap({ id: "2" }));
      fixture.detectChanges();
      expect(component.editEvent().id).toBe(2);
      expect(component.hasChanges()).toBe(false);
    });

    it("should be true after a change and false again when it is reverted", () => {
      component.editForm.name().controlValue.set("Changed");
      expect(component.hasChanges()).toBe(true);
      component.editForm.name().controlValue.set("TestHandler");
      expect(component.hasChanges()).toBe(false);
    });

    it("should be true after a change of the options, conditions, events or action", () => {
      component.setNewOptions({ opt3: "other" });
      expect(component.hasChanges()).toBe(true);
      component.setNewOptions({ opt3: "true" });
      expect(component.hasChanges()).toBe(false);
      component.setNewConditions({ condA: "true", condB: "x" });
      expect(component.hasChanges()).toBe(true);
      component.setNewConditions({ condA: "true" });
      expect(component.hasChanges()).toBe(false);
      component.setNewEvents(["eventA"]);
      expect(component.hasChanges()).toBe(true);
      component.setNewEvents(["eventA", "eventB"]);
      expect(component.hasChanges()).toBe(false);
      component.setNewAction("actionA");
      expect(component.hasChanges()).toBe(true);
    });

    it("should ignore the order of the conditions and options", () => {
      component.setNewConditions({ condB: "x", condA: "true" });
      component.setNewConditions({ condA: "true", condB: "x" });
      component.editEvent.update((handler) => ({ ...handler, conditions: { condB: "x", condA: "true" } }));
      component.event.update((handler) => ({ ...handler, conditions: { condA: "true", condB: "x" } }));
      expect(component.hasChanges()).toBe(false);
    });

    it("should treat a missing options object like an empty one", () => {
      component.event.update((handler) => ({ ...handler, options: null }));
      component.editEvent.update((handler) => ({ ...handler, options: {} }));
      expect(component.hasChanges()).toBe(false);
    });

    it("should not replace the edited event handler when the list reloads after the user changed it", () => {
      component.editForm.name().controlValue.set("Changed");
      mockEventService.eventHandlers.set([{ ...mockEventHandler, name: "Reloaded" }]);
      fixture.detectChanges();
      expect(component.editEvent().name).toBe("Changed");
    });

    it("should take over the reloaded event handler as long as the user did not change anything", () => {
      mockEventService.eventHandlers.set([{ ...mockEventHandler, name: "Reloaded" }]);
      fixture.detectChanges();
      expect(component.editEvent().name).toBe("Reloaded");
      expect(component.hasChanges()).toBe(false);
    });
  });

  it("cancelEdit should navigate back to events list", () => {
    component.cancelEdit();
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });

  it("should register hasChanges, save and validChanges with PendingChangesService on init", () => {
    expect(mockPendingChangesService.registerHasChanges).toHaveBeenCalled();
    expect(mockPendingChangesService.registerSave).toHaveBeenCalled();
    expect(mockPendingChangesService.registerValidChanges).toHaveBeenCalled();
  });

  it("should register a hasChanges that reflects the edited event handler", () => {
    const hasChanges = mockPendingChangesService.registerHasChanges.mock.calls[0][0] as () => boolean;
    expect(hasChanges()).toBe(false);
    component.editForm.name().controlValue.set("Changed");
    expect(hasChanges()).toBe(true);
  });

  it("should register the validity of the edited event handler", () => {
    const validChanges = mockPendingChangesService.registerValidChanges.mock.calls[0][0] as () => boolean;
    expect(validChanges()).toBe(true);
    component.editForm.name().controlValue.set("");
    expect(validChanges()).toBe(false);
  });

  it("should save event, reload events and navigate back", () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    const snackBarSpy = jest.spyOn(mockNotificationService, "success");
    // ensure effect is triggered to set the selected handler module in the service
    fixture.detectChanges();

    component.saveEvent();

    const convertedParams = {
      id: "1",
      name: "TestHandler",
      handlermodule: "mockModule",
      active: true,
      event: ["eventA", "eventB"],
      action: "actionB",
      "option.opt3": "true",
      conditions: { condA: "true" },
      position: "post",
      ordering: 0,
      abort_on_error: false,
      clear_options: true
    };
    expect(mockEventService.saveEventHandler).toHaveBeenCalledWith(convertedParams);
    expect(reloadSpy).toHaveBeenCalled();
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler updated successfully.");
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });

  it("should delete event, reload events and navigate back", async () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    await component.deleteEvent();
    expect(mockEventService.deleteWithConfirmDialog).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
    expect(mockPendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });

  it("should stay on the page when the deletion is not confirmed", async () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    mockEventService.deleteWithConfirmDialog.mockResolvedValue(undefined);
    await component.deleteEvent();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(mockPendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
    expect(mockRouter.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should toggle active and call enable/disable on service", () => {
    component.toggleActive(true);
    expect(mockEventService.enableEvent).toHaveBeenCalledWith(mockEventHandler.id);
    component.toggleActive(false);
    expect(mockEventService.disableEvent).toHaveBeenCalledWith(mockEventHandler.id);
  });

  it("should not save an invalid event handler, but touch all fields to show their errors", async () => {
    component.editForm.name().controlValue.set("");
    component.editEvent.update((handler) => ({ ...handler, position: "" }));
    fixture.detectChanges();
    const resolved = await component.saveEvent();
    fixture.detectChanges();
    expect(resolved).toBe(false);
    expect(mockEventService.saveEventHandler).not.toHaveBeenCalled();
    expect(component.editForm.position().touched()).toBe(true);
    const errors = Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map(
      (el) => (el as HTMLElement).textContent
    );
    expect(errors.join("|")).toContain("Selecting a position is required.");
  });

  it("should resolve to false without navigating when the save response carries no value", async () => {
    mockEventService.saveEventHandler.mockReturnValue(of({ result: {} }));
    const resolved = await component.saveEvent();
    expect(resolved).toBe(false);
    expect(mockRouter.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should resolve to false when saving the event fails", async () => {
    mockEventService.saveEventHandler.mockReturnValue(throwError(() => new Error("boom")));
    const resolved = await component.saveEvent();
    expect(resolved).toBe(false);
    expect(mockRouter.navigateByUrl).not.toHaveBeenCalled();
  });
});

describe("EventEditPageComponent — create new mode", () => {
  let component: EventEditPageComponent;
  let fixture: ComponentFixture<EventEditPageComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;
  let mockRouter: MockRouter;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventEditPageComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: Router, useClass: MockRouter },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: new BehaviorSubject(convertToParamMap({})).asObservable(),
            snapshot: { paramMap: convertToParamMap({}) }
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventEditPageComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockRouter = TestBed.inject(Router) as unknown as MockRouter;

    fixture.detectChanges();
  });

  it("should set isNewEvent to true", () => {
    expect(component.isNewEvent()).toBe(true);
  });

  it("should show 'Create New Event Handler' as title", () => {
    expect(component.title()).toContain("Create");
  });

  it("should initialize editEvent to EMPTY_EVENT", () => {
    expect(component.editEvent().name).toBe(EMPTY_EVENT.name);
    expect(component.editEvent().event).toEqual(EMPTY_EVENT.event);
  });

  it("should set selectedHandlerModule to first available module", () => {
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
  });

  it("should start with the first available module as the handler module of the new event handler", () => {
    expect(component.editEvent().handlermodule).toBe("mockModule");
    expect(component.event().handlermodule).toBe("mockModule");
    expect(component.hasChanges()).toBe(false);
  });

  it("should leave the handler module empty while the list of modules is empty", () => {
    mockEventService.eventHandlerModules = signal<string[]>([]);
    const emptyFixture = TestBed.createComponent(EventEditPageComponent);
    emptyFixture.detectChanges();
    expect(emptyFixture.componentInstance.editEvent().handlermodule).toBe("");
    expect(mockEventService.selectedHandlerModule()).toBeNull();
    expect(kinds(emptyFixture.componentInstance.editForm.handlermodule())).toEqual(["required"]);
    expect(emptyFixture.componentInstance.canSave()).toBe(false);
  });

  it("should offer the handler module for selection and write the picked module to the model and the service", async () => {
    const select = fixture.debugElement.queryAll(By.directive(MatSelect))[0].componentInstance as MatSelect;
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("mockModule");
    select.open();
    fixture.detectChanges();
    await fixture.whenStable();
    (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
    fixture.detectChanges();
    expect(component.editEvent().handlermodule).toBe("anotherModule");
    expect(component.editForm.handlermodule().dirty()).toBe(true);
    expect(mockEventService.selectedHandlerModule()).toBe("anotherModule");
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  it("should show the required error of the handler module once it is touched and block saving", () => {
    component.editForm.handlermodule().controlValue.set("");
    component.editForm.handlermodule().markAsTouched();
    fixture.detectChanges();
    expect(mockEventService.selectedHandlerModule()).toBeNull();
    expect(kinds(component.editForm.handlermodule())).toEqual(["required"]);
    expect(component.canSave()).toBe(false);
    expect(fixture.nativeElement.textContent).toContain("Selecting a handler module is required.");
  });

  describe("abort on error", () => {
    const abortToggle = () => fixture.nativeElement.querySelectorAll("mat-slide-toggle button")[1] as HTMLButtonElement;

    it("should preset abort on error from the default of the handler module", () => {
      mockEventService.moduleDefaults.set({ abort_on_error: true });
      fixture.detectChanges();

      expect(component.editEvent().abort_on_error).toBe(true);
      expect(abortToggle().getAttribute("aria-checked")).toBe("true");
      expect(component.getSaveParameters().abort_on_error).toBe(true);
      expect(component.hasChanges()).toBe(false);
    });

    it("should follow a changed default as long as the user did not decide", () => {
      mockEventService.moduleDefaults.set({ abort_on_error: true });
      fixture.detectChanges();
      mockEventService.moduleDefaults.set({ abort_on_error: false });
      fixture.detectChanges();

      expect(component.editEvent().abort_on_error).toBe(false);
    });

    it("should keep the choice of the user over the default of the handler module", () => {
      abortToggle().click();
      fixture.detectChanges();
      expect(component.editEvent().abort_on_error).toBe(true);
      expect(component.hasChanges()).toBe(true);

      abortToggle().click();
      fixture.detectChanges();
      mockEventService.moduleDefaults.set({ abort_on_error: true });
      fixture.detectChanges();

      expect(component.editEvent().abort_on_error).toBe(false);
      expect(component.getSaveParameters().abort_on_error).toBe(false);
    });

    it("should not preset abort on error while the default of the handler module is unknown", () => {
      mockEventService.moduleDefaults.set(null);
      fixture.detectChanges();

      expect(component.editEvent().abort_on_error).toBe(false);
    });
  });

  it("should save new event without id and navigate back", () => {
    component.setNewAction("actionB");
    component.setNewOptions({ opt3: "true" });
    component.setNewEvents(["eventA", "eventB"]);
    component.setNewConditions({ condA: "true" });
    component.editForm.name().controlValue.set("TestHandler");
    component.editForm.position().controlValue.set("pre");

    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    const snackBarSpy = jest.spyOn(mockNotificationService, "success");
    component.saveEvent();

    const convertedParams = {
      name: "TestHandler",
      handlermodule: "mockModule",
      active: true,
      event: ["eventA", "eventB"],
      action: "actionB",
      "option.opt3": "true",
      conditions: { condA: "true" },
      position: "pre",
      ordering: 0,
      abort_on_error: false,
      clear_options: true
    };
    expect(mockEventService.saveEventHandler).toHaveBeenCalledWith(convertedParams);
    expect(reloadSpy).toHaveBeenCalled();
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler created successfully.");
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });

  it("should not call enable/disable while the event has not been saved yet", () => {
    component.toggleActive(true);
    expect(mockEventService.enableEvent).not.toHaveBeenCalled();
    expect(mockEventService.disableEvent).not.toHaveBeenCalled();
  });
});
