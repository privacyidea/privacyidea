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
import { OutputEmitterRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AuthService } from "@services/auth/auth.service";
import { EventService } from "@services/event/event.service";
import { WebhookService } from "@services/webhook/webhook.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { MockWebhookService } from "@testing/mock-services/mock-webhook-service";
import { EventActionOptionValues, EventActionTabComponent } from "./event-action-tab.component";

describe("EventActionTabComponent", () => {
  let component: EventActionTabComponent;
  let fixture: ComponentFixture<EventActionTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventActionTabComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService },
        { provide: WebhookService, useClass: MockWebhookService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventActionTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("action", "add_token_info");
    fixture.componentRef.setInput("options", { key: "test_key", value: "test_value" });
    component.newAction = { emit: jest.fn() } as unknown as OutputEmitterRef<string>;
    component.newOptions = { emit: jest.fn() } as unknown as OutputEmitterRef<EventActionOptionValues>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize selectedAction from input", () => {
    expect(component.selectedAction()).toBe("add_token_info");
  });

  it("should reset options on action selection change and emit changes", () => {
    component.selectedAction.set("actionB");
    fixture.detectChanges();
    expect(Object.keys(component.selectedOptions())).toEqual(["opt3"]);
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt3: "" });
  });

  it("should update selectedOptions and emit on option change", () => {
    component.setOption("key", "another_key");
    component.setOption("value", "");
    fixture.detectChanges();

    expect(component.selectedOptions()).toEqual({ key: "another_key", value: "" });
    expect(component.newOptions.emit).toHaveBeenCalledWith({ key: "another_key", value: "" });
  });

  it("should also emit empty options", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    expect(Object.keys(component.selectedOptions())).toEqual(["opt1", "opt2", "opt3"]);
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt1: "", opt2: "", opt3: "" });

    component.setOption("opt3", "newValue");
    fixture.detectChanges();
    expect(component.selectedOptions()).toEqual({ opt1: "", opt2: "", opt3: "newValue" });
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt1: "", opt2: "", opt3: "newValue" });
  });

  it("onActionSelectionChange should emit selected action", () => {
    component.onActionSelectionChange("actionB");
    expect(component.newAction.emit).toHaveBeenCalledWith("actionB");

    component.onActionSelectionChange("");
    expect(component.newAction.emit).toHaveBeenCalledWith("");
  });

  it("actionOptions() should return empty dict if no action is selected", () => {
    component.selectedAction.set("");
    fixture.componentRef.setInput("action", "");
    fixture.detectChanges();
    const opts = component.actionOptions();
    expect(opts).toMatchObject({});
  });

  it("actionOptions() should return options for selected action", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    const opts = component.actionOptions();
    expect(opts["opt1"].type).toBe("bool");
    expect(opts["opt2"].type).toBe("int");
  });

  describe("orderedOptionNames", () => {
    it("follows the order the handler module states, not the one the response carries", () => {
      // Flask serialises with sort_keys, so the options arrive alphabetically - "webhook" last -
      // however the handler module writes them. Without the stated order it would show up there.
      fixture.componentRef.setInput("action", "post_webhook");
      fixture.detectChanges();

      expect(component.orderedOptionNames()).toEqual(["webhook", "URL", "content_type", "data", "replace"]);
    });

    it("renders the fields in that order", () => {
      // The method alone is not enough: the template has to iterate it. With the template back on
      // Object.keys() every assertion on orderedOptionNames() still passes while the page shows
      // "webhook" last, which is the bug this guards.
      fixture.componentRef.setInput("action", "post_webhook");
      fixture.detectChanges();

      const rendered = (Array.from(fixture.nativeElement.querySelectorAll("div.pad-0")) as HTMLElement[]).map(
        (wrapper) => {
          const label = wrapper.querySelector("mat-label") ?? wrapper.querySelector("mat-checkbox");
          return (label?.textContent ?? "").trim();
        }
      );

      expect(rendered).toEqual(["webhook", "URL", "content_type", "data", "replace"]);
    });

    it("gives the payload a textarea at the wider size", () => {
      // A webhook payload is a JSON document, not a word, so it gets the treatment the
      // notification handler's message bodies get rather than a one-line input.
      fixture.componentRef.setInput("action", "post_webhook");
      fixture.detectChanges();

      const wrappers = Array.from(fixture.nativeElement.querySelectorAll("div.pad-0")) as HTMLElement[];
      const payload = wrappers.find((w) => (w.querySelector("mat-label")?.textContent ?? "").trim() === "data");

      expect(payload?.querySelector("textarea")).toBeTruthy();
      expect(payload?.querySelector("mat-form-field")?.classList).toContain("input-width-xl");
    });

    it("will not let the handler be saved without a webhook", () => {
      // The endpoint lives on the webhook and URL is not editable, so a handler saved without one
      // would have nowhere to post and silently do nothing.
      fixture.componentRef.setInput("action", "post_webhook");
      fixture.componentRef.setInput("options", {});
      fixture.detectChanges();
      expect(component.optionsAreValid()).toBe(false);

      component.selectedOptions.update((options) => ({ ...options, webhook: "siem" }));
      expect(component.optionsAreValid()).toBe(true);
    });

    it("leaves a module that states no order alone", () => {
      fixture.componentRef.setInput("action", "add_token_info");
      fixture.detectChanges();

      expect(component.orderedOptionNames()).toEqual(["key", "value"]);
    });
  });

  describe("readonlyDisplayValue", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("action", "post_webhook");
      fixture.componentRef.setInput("options", { URL: "https://stored.example.com/hook" });
      fixture.detectChanges();
    });

    it("shows the stored value while no webhook is selected", () => {
      // A handler still on the inline shape: the URL in the database is where it posts.
      expect(component.readonlyDisplayValue("URL")).toBe("https://stored.example.com/hook");
    });

    it("shows the selected webhook's field instead of the stored value", () => {
      // Selecting a webhook replaces the inline endpoint, so the field has to follow the
      // selection rather than keep naming an endpoint the handler no longer posts to.
      const webhookService = TestBed.inject(WebhookService) as unknown as MockWebhookService;
      webhookService.webhooks.set([
        {
          identifier: "siem",
          url: "https://siem.example.com/hook",
          content_type: "application/json"
        } as never
      ]);
      component.selectedOptions.update((options) => ({ ...options, webhook: "siem" }));

      expect(component.readonlyDisplayValue("URL")).toBe("https://siem.example.com/hook");
      expect(component.readonlyDisplayValue("content_type")).toBe("application/json");
    });

    it("shows nothing when the selected webhook cannot be resolved", () => {
      // /webhook/ needs webhook_read, and the identifier may name a webhook since deleted. The
      // stored inline value would name an endpoint this handler does not post to.
      component.selectedOptions.update((options) => ({ ...options, webhook: "gone" }));

      expect(component.readonlyDisplayValue("URL")).toBe("");
    });

    it("leaves an editable option alone", () => {
      component.selectedOptions.update((options) => ({ ...options, data: "{}" }));

      expect(component.readonlyDisplayValue("data")).toBe("{}");
    });
  });

  it("checkOptionVisibility returns true if no visibleIf", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt1")).toBe(true);
  });

  it("checkOptionVisibility returns true if visibleIf is set and value matches", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true, opt2: "3" });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt3")).toBe(true);
  });

  it("checkOptionVisibility returns false if visibleIf is set and value does not match", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true, opt2: "1" });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt3")).toBe(false);
  });

  it("checkOptionVisibility returns true if visibleIf is set, but not visibleValue and dependent value is set", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt2")).toBe(true);
  });
});
