import { TestBed } from "@angular/core/testing";
import { HttpClient, HttpParams } from "@angular/common/http";
import { lastValueFrom, of } from "rxjs";

import { MachineService } from "./machine.service";

import { LocalService } from "../local/local.service";
import { TableUtilsService } from "../table-utils/table-utils.service";
import { ContentService } from "../content/content.service";
import { environment } from "../../../environments/environment";
import {
  MockContentService,
  MockLocalService,
  MockTableUtilsService
} from "../../../testing/mock-services";

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
        MachineService
      ]
    });

    httpStub.get.mockReturnValue(of({}));

    machineService = TestBed.inject(MachineService);
  });

  it("postAssignMachineToToken posts args with auth header", async () => {
    httpStub.post.mockReturnValue(of({ ok: true }));
    const args = {
      service_id: "svc",
      user: "alice",
      serial: "serial",
      application: "ssh",
      machineid: "MID",
      resolver: "RES"
    };
    await lastValueFrom(machineService.postAssignMachineToToken(args));
    expect(httpStub.post).toHaveBeenCalledWith("/api/machine/token", args, {
      headers: { Authorization: "Bearer x" }
    });
  });

  it("postTokenOption builds correct request body", async () => {
    httpStub.post.mockReturnValue(of({}));
    await lastValueFrom(
      machineService.postTokenOption("host", "mid", "res", "serial", "ssh", "mtid")
    );
    expect(httpStub.post).toHaveBeenCalledWith(
      "/api/machine/tokenoption",
      {
        hostname: "host",
        machineid: "mid",
        resolver: "res",
        serial: "serial",
        application: "ssh",
        mtid: "mtid"
      },
      { headers: { Authorization: "Bearer x" } }
    );
  });

  it("postToken hits /token endpoint", async () => {
    httpStub.post.mockReturnValue(of({}));
    await lastValueFrom(machineService.postToken("host", "mid", "res", "serial", "offline"));
    expect(httpStub.post).toHaveBeenCalledWith(
      "/api/machine/token",
      {
        hostname: "host",
        machineid: "mid",
        resolver: "res",
        serial: "serial",
        application: "offline"
      },
      { headers: { Authorization: "Bearer x" } }
    );
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
    expect(httpStub.delete).toHaveBeenCalledWith("/api/machine/token/S/M/R/ssh", {
      headers: { Authorization: "Bearer x" }
    });
    await lastValueFrom(machineService.deleteTokenMtid("S2", "offline", "MT"));
    expect(httpStub.delete).toHaveBeenCalledWith("/api/machine/token/S2/offline/MT", {
      headers: { Authorization: "Bearer x" }
    });
  });

  it("filterParams produces expected object for ssh", () => {
    machineService.filterValue.set({ serial: "abc", hostname: "host" });
    expect(machineService.filterParams()).toEqual({
      serial: "*abc*",
      hostname: "host"
    });
  });

  it("filterParams handles offline application type", () => {
    machineService.selectedApplicationType.set("offline");
    machineService.filterValue.set({
      serial: "xyz",
      hostname: "h",
      count: "5",
      rounds: "10",
      service_id: "svc"
    } as any);
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
