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
import { HttpClient, HttpHeaders, HttpParams } from "@angular/common/http";
import {
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService
} from "../../../testing/mock-services";
import { lastValueFrom, of } from "rxjs";

import { ContentService } from "../content/content.service";
import { LocalService } from "../local/local.service";
import { MachineService } from "./machine.service";
import { TableUtilsService } from "../table-utils/table-utils.service";
import { TestBed } from "@angular/core/testing";
import { environment } from "../../../environments/environment";
import { FilterValue } from "../../core/models/filter_value";

environment.proxyUrl = "/api";

const httpStub = {
  get: jest.fn(),
  post: jest.fn(),
  delete: jest.fn()
};

describe("MachineService (with mock classes)", () => {
  let machineService: MachineService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: HttpClient, useValue: httpStub },
        { provide: LocalService, useClass: MockLocalService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        MachineService,
        MockLocalService,
        MockNotificationService
      ]
    });

    httpStub.get.mockReturnValue(of({}));

    machineService = TestBed.inject(MachineService);
  });

  it("postAssignMachineToToken posts args with auth header", async () => {
    httpStub.post.mockReturnValue(of({ ok: true }));
    await lastValueFrom(
      machineService.postAssignMachineToToken({
        service_id: "svc",
        user: "alice",
        serial: "serial",
        application: "ssh",
        machineid: 0,
        resolver: "RES"
      })
    );
    const [url, body, opts] = (httpStub.post as jest.Mock).mock.calls[0];
    expect(url).toBe("/api/machine/token");
    expect(body).toEqual({
      service_id: "svc",
      user: "alice",
      serial: "serial",
      application: "ssh",
      machineid: 0,
      resolver: "RES"
    });
    expect(opts.headers instanceof HttpHeaders).toBe(true);
  });

  it("postTokenOption builds correct request body", async () => {
    httpStub.post.mockReturnValue(of({}));
    await lastValueFrom(machineService.postTokenOption("host", "mid", "res", "serial", "ssh", "mtid"));
    const [url, body, opts] = (httpStub.post as jest.Mock).mock.calls[0];
    expect(url).toBe("/api/machine/tokenoption");
    expect(body).toEqual({
      hostname: "host",
      machineid: "mid",
      resolver: "res",
      serial: "serial",
      application: "ssh",
      mtid: "mtid"
    });
    expect(opts.headers instanceof HttpHeaders).toBe(true);
  });

  it("postToken hits /token endpoint", async () => {
    httpStub.post.mockReturnValue(of({}));
    await lastValueFrom(machineService.postToken("host", "mid", "res", "serial", "offline"));
    const [url, body, opts] = (httpStub.post as jest.Mock).mock.calls[0];
    expect(url).toBe("/api/machine/token");
    expect(body).toEqual({
      hostname: "host",
      machineid: "mid",
      resolver: "res",
      serial: "serial",
      application: "offline"
    });
    expect(opts.headers instanceof HttpHeaders).toBe(true);
  });

  it("getAuthItem chooses URL with and without application", () => {
    httpStub.get.mockReturnValue(of({}));

    machineService.getAuthItem("ch", "h", "ssh").subscribe();
    const [, optsA] = httpStub.get.mock.calls.at(-1);
    expect(httpStub.get).toHaveBeenLastCalledWith("/api/machine/authitem/ssh", expect.any(Object));
    expect(optsA.params.get("challenge")).toBe("ch");
    expect(optsA.params.get("hostname")).toBe("h");

    machineService.getAuthItem("c2", "h2").subscribe();
    const [urlB, optsB] = httpStub.get.mock.calls.at(-1);
    expect(urlB).toBe("/api/machine/authitem");
    expect(optsB.params.get("challenge")).toBe("c2");
    expect(optsB.params.get("hostname")).toBe("h2");
  });

  it("getMachine forwards only defined params", () => {
    httpStub.get.mockReturnValue(of({}));
    machineService
      .getMachine({
        hostname: "h",
        ip: "1.2.3.4",
        id: "ID",
        resolver: "R",
        any: "X"
      })
      .subscribe();

    const [, opts] = httpStub.get.mock.calls.at(-1);
    const p = opts.params as HttpParams;
    expect(p.get("hostname")).toBe("h");
    expect(p.get("ip")).toBe("1.2.3.4");
    expect(p.get("id")).toBe("ID");
    expect(p.get("resolver")).toBe("R");
    expect(p.get("any")).toBe("X");
  });

  it("deleteToken & deleteTokenMtid craft correct URLs", async () => {
    httpStub.delete.mockReturnValue(of({}));
    await lastValueFrom(machineService.deleteToken("S", "M", "R", "ssh"));
    const [url] = (httpStub.delete as jest.Mock).mock.calls[0];
    expect(url).toBe("/api/machine/token/S/M/R/ssh");
    await lastValueFrom(machineService.deleteTokenMtid("S2", "offline", "MT"));
    const [url2] = (httpStub.delete as jest.Mock).mock.calls[1];
    expect(url2).toBe("/api/machine/token/S2/offline/MT");
  });

  it("filterParams produces expected object for ssh", () => {
    machineService.machineFilter.set(new FilterValue({ value: "serial:abc hostname:host" }));
    expect(machineService.filterParams()).toEqual({
      serial: "*abc*",
      hostname: "host"
    });
  });

  it("filterParams handles offline application type", () => {
    machineService.selectedApplicationType.set("offline");
    machineService.machineFilter.set(
      new FilterValue({ value: "serial:xyz hostname:h count:5 rounds:10 service_id:svc" })
    );

    expect(machineService.filterParams()).toEqual({
      serial: "*xyz*",
      hostname: "h",
      count: "5",
      rounds: "10"
    });
  });

  it("onPageEvent & onSortEvent update linked signals", () => {
    machineService.onPageEvent({ pageSize: 25, pageIndex: 3 } as any);
    expect(machineService.pageSize()).toBe(25);
    expect(machineService.pageIndex()).toBe(3);

    machineService.onSortEvent({
      active: "hostname",
      direction: "desc"
    } as any);
    expect(machineService.sort()).toEqual({
      active: "hostname",
      direction: "desc"
    });
  });
});
