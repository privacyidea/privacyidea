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

import { SourceIpCell } from "./source-ip-cell";

describe("SourceIpCell", () => {
  let component: SourceIpCell;
  let fixture: ComponentFixture<SourceIpCell>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SourceIpCell] }).compileComponents();
    fixture = TestBed.createComponent(SourceIpCell);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("sourceIp", "203.0.113.5");
  });

  function setInputs(inputs: Record<string, unknown>): void {
    for (const [name, value] of Object.entries(inputs)) {
      fixture.componentRef.setInput(name, value);
    }
    fixture.detectChanges();
  }

  it("names where the shown address came from", () => {
    setInputs({ sourceIpSource: "X_FORWARDED_FOR" });
    expect(component.badge()?.label).toBe("proxy");
    setInputs({ sourceIpSource: "REMOTE_ADDR" });
    expect(component.badge()?.label).toBe("direct");
    setInputs({ sourceIpSource: "REMOTE_ADDR_UNMAPPED" });
    expect(component.badge()?.label).toBe("unmapped");
  });

  // An entry written before the recording says nothing about its derivation, and "direct" would be a guess.
  it("shows no badge for an entry that does not record its derivation", () => {
    setInputs({ sourceIpSource: null });
    expect(component.badge()).toBeNull();
    expect(fixture.nativeElement.querySelector(".ip-source-badge")).toBeNull();
  });

  it("shows no badge for a derivation it has no wording for", () => {
    setInputs({ sourceIpSource: "SOMETHING_NEW" });
    expect(component.badge()).toBeNull();
  });

  it("offers no expansion when there is nothing more to say", () => {
    setInputs({ peerIp: "203.0.113.5", ipChain: null });
    expect(component.canExpand()).toBe(false);
    expect(fixture.nativeElement.querySelector(".source-ip-toggle")).toBeNull();
  });

  it("expands when the request arrived from a different address", () => {
    setInputs({ peerIp: "10.0.0.17" });
    expect(component.showsPeer()).toBe(true);
    expect(component.canExpand()).toBe(true);
  });

  it("renders the claimed path in order and marks the effective hop", () => {
    setInputs({
      peerIp: "10.0.0.17",
      ipChain: [
        { ip: "10.0.0.17", source: "REMOTE_ADDR" },
        { ip: "203.0.113.5", source: "X_FORWARDED_FOR", effective: true }
      ]
    });
    component.toggle();
    fixture.detectChanges();

    const hops: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll(".info-sublist li"));
    expect(hops.map((hop) => hop.textContent?.trim().split(" ")[0])).toEqual(["10.0.0.17", "203.0.113.5"]);
    expect(hops[1].classList).toContain("ip-hop-effective");
    expect(hops[0].textContent).toContain("connection");
    expect(hops[1].textContent).toContain("X-Forwarded-For");
  });

  it("emits a filter request for the effective address and for the peer", () => {
    const emitted: { key: string; value: string }[] = [];
    component.filterValue.subscribe((event) => emitted.push(event));
    component.onFilter("source_ip", "203.0.113.5");
    component.onFilter("peer_ip", "10.0.0.17");
    expect(emitted).toEqual([
      { key: "source_ip", value: "203.0.113.5" },
      { key: "peer_ip", value: "10.0.0.17" }
    ]);
  });
});
