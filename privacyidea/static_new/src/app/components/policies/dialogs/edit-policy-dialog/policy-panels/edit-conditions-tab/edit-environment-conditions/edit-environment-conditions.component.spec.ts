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
import { MatSelect, MatSelectChange } from "@angular/material/select";
import { EditEnvironmentConditionsComponent } from "@components/policies/dialogs/edit-policy-dialog/policy-panels/edit-conditions-tab/edit-environment-conditions/edit-environment-conditions.component";
import { ClientsDict, ClientsService } from "@services/clients/clients.service";
import { PolicyService } from "@services/policies/policies.service";
import { SystemService } from "@services/system/system.service";
import { MockClientsService, MockPolicyService, MockSystemService } from "@testing/mock-services";

describe("EditEnvironmentConditionsComponent", () => {
  let component: EditEnvironmentConditionsComponent;
  let fixture: ComponentFixture<EditEnvironmentConditionsComponent>;
  let clientsMock: MockClientsService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditEnvironmentConditionsComponent],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: ClientsService, useClass: MockClientsService }
      ]
    }).compileComponents();

    clientsMock = TestBed.inject(ClientsService) as unknown as MockClientsService;

    fixture = TestBed.createComponent(EditEnvironmentConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", {
      name: "test-policy",
      user_agents: ["PAM"],
      time: "Mon-Fri: 9-18",
      client: ["10.0.0.0/8"]
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form controls with policy values", () => {
    expect(component.validTimeSignal()).toBe("Mon-Fri: 9-18");
    expect(component.clientSignal()).toBe("10.0.0.0/8");
  });

  it("falls back to empty strings when policy has no time or client", () => {
    const freshFixture = TestBed.createComponent(EditEnvironmentConditionsComponent);
    freshFixture.componentRef.setInput("policy", { name: "no-env-policy" });
    freshFixture.detectChanges();
    const fresh = freshFixture.componentInstance;
    expect(fresh.validTimeSignal()).toBe("");
    expect(fresh.clientSignal()).toBe("");
  });

  it("requests known clients for autocomplete on init", () => {
    expect(clientsMock.requestClientsForAutocomplete).toHaveBeenCalled();
  });

  it("should validate client format correctly", () => {
    component.clientSignal.set("invalid-ip");
    expect(component.clientField().valid()).toBe(false);

    component.clientSignal.set("192.168.1.1");
    expect(component.clientField().valid()).toBe(true);
  });

  it("should emit edits when adding a user agent", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.addUserAgentSignal.set("NewAgent");
    component.addUserAgent();
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        user_agents: ["PAM", "NewAgent"]
      })
    );
  });

  it("should clear valid time control", () => {
    component.clearValidTimeControl();
    expect(component.validTimeSignal()).toBe("");
  });

  describe("knownClients", () => {
    it("aggregates clients across applications, dedupes apps, and sorts by IP", () => {
      clientsMock.setClients({
        "App B": [{ ip: "10.0.0.2" }, { ip: "10.0.0.1", hostname: "host-one" }, { ip: "10.0.0.1" }],
        "App A": [{ ip: "10.0.0.1" }, { ip: "10.0.0.3", hostname: "host-three" }]
      });

      const result = component.knownClients();

      expect(result.map((c) => c.ip)).toEqual(["10.0.0.1", "10.0.0.2", "10.0.0.3"]);
      const first = result[0];
      expect(first.hostname).toBe("host-one");
      expect(first.applications).toEqual(["App B", "App A"]);
    });

    it("skips entries without an IP", () => {
      clientsMock.setClients({
        App: [{ ip: "10.0.0.1" }, { hostname: "ghost" }]
      });

      expect(component.knownClients()).toHaveLength(1);
    });

    it("backfills hostname from a later entry if the first entry has none", () => {
      clientsMock.setClients({
        "App A": [{ ip: "10.0.0.1" }],
        "App B": [{ ip: "10.0.0.1", hostname: "filled-later" }]
      });

      expect(component.knownClients()[0].hostname).toBe("filled-later");
    });

    it("returns an empty list when no clients data is available", () => {
      expect(component.knownClients()).toEqual([]);
    });
  });

  describe("filteredKnownClients", () => {
    beforeEach(() => {
      clientsMock.setClients({
        MyApp: [
          { ip: "10.0.0.1", hostname: "server-one.example.com" },
          { ip: "192.168.1.1", hostname: "router.local" },
          { ip: "172.16.0.5" }
        ],
        OtherApp: [{ ip: "10.0.0.1" }]
      });
    });

    it("returns all clients when no search term is entered", () => {
      component.clientSignal.set("");
      expect(component.filteredKnownClients()).toHaveLength(3);
    });

    it("filters by IP substring", () => {
      component.clientSignal.set("192.168");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("filters by hostname case-insensitively", () => {
      component.clientSignal.set("ROUTER");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("filters by application name", () => {
      component.clientSignal.set("otherapp");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["10.0.0.1"]);
    });

    it("strips a leading exclamation mark from the search term", () => {
      component.clientSignal.set("!192.168");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("uses only the segment after the last comma", () => {
      component.clientSignal.set("10.0.0.0/8, !192");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("limits the result to at most 20 entries", () => {
      const dict: ClientsDict = { App: [] };
      for (let i = 0; i < 30; i++) {
        dict["App"].push({ ip: `10.0.0.${i}` });
      }
      clientsMock.setClients(dict);
      component.clientSignal.set("");
      expect(component.filteredKnownClients()).toHaveLength(20);
    });
  });

  describe("addUserAgentFromSelect", () => {
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    it("emits the selected value and clears the MatSelect after the timer flushes", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      const selectRef = { value: "Keycloak" } as unknown as MatSelect;

      component.addUserAgentFromSelect({ value: "Keycloak" } as MatSelectChange, selectRef);

      expect(spy).toHaveBeenCalledWith({ user_agents: ["PAM", "Keycloak"] });
      expect(selectRef.value).toBe("Keycloak");
      jest.runAllTimers();
      expect(selectRef.value).toBeNull();
    });

    it("does not emit when the selected value is empty but still clears the select", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      const selectRef = { value: "" } as unknown as MatSelect;

      component.addUserAgentFromSelect({ value: "" } as MatSelectChange, selectRef);
      jest.runAllTimers();

      expect(spy).not.toHaveBeenCalled();
      expect(selectRef.value).toBeNull();
    });

    it("does not re-emit when the user agent is already selected", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      const selectRef = { value: "PAM" } as unknown as MatSelect;

      component.addUserAgentFromSelect({ value: "PAM" } as MatSelectChange, selectRef);
      jest.runAllTimers();

      expect(spy).not.toHaveBeenCalled();
    });
  });

  describe("handleEnterOnSearch", () => {
    function makeEvent(): Event {
      return {
        preventDefault: jest.fn(),
        stopPropagation: jest.fn()
      } as unknown as Event;
    }

    function makeSelect(): MatSelect {
      return { close: jest.fn() } as unknown as MatSelect;
    }

    it("prevents default and stops propagation on the event", () => {
      const event = makeEvent();
      component.handleEnterOnSearch(event, makeSelect());
      expect(event.preventDefault).toHaveBeenCalled();
      expect(event.stopPropagation).toHaveBeenCalled();
    });

    it("adds the first filtered preset, clears the search, and closes the select", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      const select = makeSelect();
      component.userAgentSearch.set("key");

      component.handleEnterOnSearch(makeEvent(), select);

      expect(spy).toHaveBeenCalledWith({ user_agents: ["PAM", "Keycloak"] });
      expect(component.userAgentSearch()).toBe("");
      expect(select.close).toHaveBeenCalled();
    });

    it("uses the first remaining preset when no search term is set", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      const select = makeSelect();

      component.handleEnterOnSearch(makeEvent(), select);

      expect(spy).toHaveBeenCalledWith({ user_agents: ["PAM", "Credential Provider"] });
      expect(select.close).toHaveBeenCalled();
    });

    it("does nothing when no preset matches the search", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      const select = makeSelect();
      component.userAgentSearch.set("no-such-preset");

      component.handleEnterOnSearch(makeEvent(), select);

      expect(spy).not.toHaveBeenCalled();
      expect(component.userAgentSearch()).toBe("no-such-preset");
      expect(select.close).not.toHaveBeenCalled();
    });

    it("does nothing when every preset is already selected", () => {
      fixture.componentRef.setInput("policy", {
        name: "test-policy",
        user_agents: [...component.userAgentPresets]
      });
      fixture.detectChanges();
      const spy = jest.spyOn(component.policyEdit, "emit");
      const select = makeSelect();

      component.handleEnterOnSearch(makeEvent(), select);

      expect(spy).not.toHaveBeenCalled();
      expect(select.close).not.toHaveBeenCalled();
    });
  });

  describe("setClients", () => {
    it("does not emit when the client value is invalid", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      component.clientSignal.set("not-an-ip");
      expect(spy).not.toHaveBeenCalled();
    });

    it("emits an empty client array when the model is cleared", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      component.clientSignal.set("");
      fixture.detectChanges();
      expect(spy).toHaveBeenCalledWith({ client: [] });
    });

    it("splits, trims, and drops empty segments when emitting", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      component.clientSignal.set("10.0.0.1 ,  192.168.1.1 , ");
      fixture.detectChanges();
      expect(spy).toHaveBeenCalledWith({ client: ["10.0.0.1", "192.168.1.1"] });
    });
  });

  describe("clearClientControl", () => {
    it("resets the client model to an empty string", () => {
      component.clientSignal.set("10.0.0.1");
      component.clearClientControl();
      expect(component.clientSignal()).toBe("");
    });
  });

  describe("clientSignal effect", () => {
    it("does not emit a client edit during initialization from policy.client", () => {
      const freshFixture = TestBed.createComponent(EditEnvironmentConditionsComponent);
      const fresh = freshFixture.componentInstance;
      const spy = jest.spyOn(fresh.policyEdit, "emit");
      freshFixture.componentRef.setInput("policy", {
        name: "init-policy",
        client: ["10.0.0.1", "192.168.1.1"]
      });
      freshFixture.detectChanges();
      expect(spy).not.toHaveBeenCalledWith(expect.objectContaining({ client: expect.anything() }));
      expect(fresh.clientSignal()).toBe("10.0.0.1, 192.168.1.1");
    });

    it("re-emits on every subsequent clientSignal change", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      component.clientSignal.set("10.0.0.1");
      fixture.detectChanges();
      component.clientSignal.set("192.168.1.1");
      fixture.detectChanges();
      const clientCalls = spy.mock.calls.filter((c) => "client" in (c[0] as object));
      expect(clientCalls).toEqual([[{ client: ["10.0.0.1"] }], [{ client: ["192.168.1.1"] }]]);
    });
  });

  describe("buildClientSelection", () => {
    it("returns the IP with a trailing ', ' when the form control is empty", () => {
      component.clientSignal.set("");
      expect(component.buildClientSelection("10.0.0.1")).toBe("10.0.0.1, ");
    });

    it("replaces the current incomplete segment when there is no comma", () => {
      component.clientSignal.set("10.0");
      expect(component.buildClientSelection("10.0.0.1")).toBe("10.0.0.1, ");
    });

    it("appends the IP after the last comma with a leading space", () => {
      component.clientSignal.set("10.0.0.0/8,");
      expect(component.buildClientSelection("192.168.1.1")).toBe("10.0.0.0/8, 192.168.1.1, ");
    });

    it("preserves a leading '!' negation marker on the current segment", () => {
      component.clientSignal.set("10.0.0.0/8, !19");
      expect(component.buildClientSelection("192.168.1.1")).toBe("10.0.0.0/8, !192.168.1.1, ");
    });

    it("preserves a '!' negation marker when it is the first character", () => {
      component.clientSignal.set("!19");
      expect(component.buildClientSelection("192.168.1.1")).toBe("!192.168.1.1, ");
    });

    it("keeps the space after the comma when a partial IP has already been typed", () => {
      component.clientSignal.set("127.0.0.1, 10");
      expect(component.buildClientSelection("10.0.0.1")).toBe("127.0.0.1, 10.0.0.1, ");
    });

    it("clears the autocomplete filter so all known clients show again", () => {
      clientsMock.setClients({
        App: [
          { ip: "10.0.0.1" },
          { ip: "10.0.0.2" },
          { ip: "192.168.1.1" }
        ]
      });
      component.clientSignal.set(component.buildClientSelection("10.0.0.1"));
      expect(component.clientSearchTerm()).toBe("");
      expect(component.filteredKnownClients()).toHaveLength(3);
    });
  });
});
