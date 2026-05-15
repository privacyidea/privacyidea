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
import { ReactiveFormsModule } from "@angular/forms";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { ClientsDict, ClientsService } from "@services/clients/clients.service";
import { PolicyService } from "@services/policies/policies.service";
import { SystemService } from "@services/system/system.service";
import { MockClientsService } from "@testing/mock-services/mock-clients-service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { EditEnvironmentConditionsComponent } from "./edit-environment-conditions.component";

describe("EditEnvironmentConditionsComponent", () => {
  let component: EditEnvironmentConditionsComponent;
  let fixture: ComponentFixture<EditEnvironmentConditionsComponent>;
  let clientsMock: MockClientsService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditEnvironmentConditionsComponent, ReactiveFormsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: ClientsService, useClass: MockClientsService },
        provideNoopAnimations()
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
    expect(component.validTimeFormControl.value).toBe("Mon-Fri: 9-18");
    expect(component.clientFormControl.value).toBe("10.0.0.0/8");
  });

  it("should validate client format correctly", () => {
    component.clientFormControl.setValue("invalid-ip");
    expect(component.clientFormControl.invalid).toBe(true);

    component.clientFormControl.setValue("192.168.1.1");
    expect(component.clientFormControl.valid).toBe(true);
  });

  it("should emit edits when adding a user agent", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.addUserAgentFormControl.setValue("NewAgent");
    component.addUserAgent();
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        user_agents: ["PAM", "NewAgent"]
      })
    );
  });

  it("should clear valid time control", () => {
    component.clearValidTimeControl();
    expect(component.validTimeFormControl.value).toBe("");
  });

  describe("knownClients", () => {
    it("aggregates clients across applications, dedupes apps, and sorts by IP", () => {
      clientsMock.setClients({
        "App B": [
          { ip: "10.0.0.2" },
          { ip: "10.0.0.1", hostname: "host-one" },
          { ip: "10.0.0.1" }
        ],
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
      component.clientFormControl.setValue("");
      expect(component.filteredKnownClients()).toHaveLength(3);
    });

    it("filters by IP substring", () => {
      component.clientFormControl.setValue("192.168");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("filters by hostname case-insensitively", () => {
      component.clientFormControl.setValue("ROUTER");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("filters by application name", () => {
      component.clientFormControl.setValue("otherapp");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["10.0.0.1"]);
    });

    it("strips a leading exclamation mark from the search term", () => {
      component.clientFormControl.setValue("!192.168");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("uses only the segment after the last comma", () => {
      component.clientFormControl.setValue("10.0.0.0/8, !192");
      expect(component.filteredKnownClients().map((c) => c.ip)).toEqual(["192.168.1.1"]);
    });

    it("limits the result to at most 20 entries", () => {
      const dict: ClientsDict = { App: [] };
      for (let i = 0; i < 30; i++) {
        dict["App"].push({ ip: `10.0.0.${i}` });
      }
      clientsMock.setClients(dict);
      component.clientFormControl.setValue("");
      expect(component.filteredKnownClients()).toHaveLength(20);
    });
  });
});
