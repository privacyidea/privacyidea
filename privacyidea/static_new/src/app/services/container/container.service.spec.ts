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
import { ContainerDetails, ContainerService } from "./container.service";
import { HttpClient, HttpErrorResponse, HttpParams, provideHttpClient } from "@angular/common/http";
import {
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTokenService
} from "../../../testing/mock-services";
import { lastValueFrom, of, throwError } from "rxjs";
import { NotificationService } from "../notification/notification.service";
import { TestBed } from "@angular/core/testing";
import { TokenService } from "../token/token.service";
import { AuthService } from "../auth/auth.service";
import { FilterValue } from "../../core/models/filter_value";
import { ROUTE_PATHS } from "../../route_paths";
import { ContentService } from "../content/content.service";


class MockAuthService implements Partial<AuthService> {
  getHeaders = jest.fn().mockReturnValue({ Authorization: "Bearer FAKE_TOKEN" });
  actionAllowed = jest.fn().mockReturnValue(true);
}

describe("ContainerService", () => {
  let containerService: ContainerService;
  let http: HttpClient;
  let authService: MockAuthService;
  let notificationService: MockNotificationService;
  let tokenService: MockTokenService;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        MockLocalService,
        MockNotificationService
      ]
    });
    containerService = TestBed.inject(ContainerService);
    http = TestBed.inject(HttpClient);
    authService = TestBed.inject(AuthService) as any;
    notificationService = TestBed.inject(NotificationService) as any;
    tokenService = TestBed.inject(TokenService) as any;
    contentService = TestBed.inject(ContentService) as any;
  });

  it("creates the service", () => {
    expect(containerService).toBeTruthy();
  });

  it("assignContainer posts payload and returns result", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: true } as any));
    const r = await lastValueFrom(containerService.addToken("tok1", "cont1"));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cont1/add`,
      { serial: "tok1" },
      expect.objectContaining({ headers: expect.anything() })
    );
    expect(r).toEqual({ result: true });
  });

  it("assignContainer propagates error and shows snackbar", async () => {
    jest.spyOn(http, "post").mockReturnValue(throwError(() => ({ status: 400, error: {} })));
    await expect(lastValueFrom(containerService.addToken("tokX", "contX"))).rejects.toBeDefined();
    expect(notificationService.openSnackBar).toHaveBeenCalled();
  });

  it("toggleActive switches active → disabled", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { disabled: true } } as any));
    await lastValueFrom(containerService.toggleActive("c1", ["active"]));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c1/states`,
      { states: "disabled" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("toggleActive adds active when no state present", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { active: true } } as any));
    await lastValueFrom(containerService.toggleActive("c2", []));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c2/states`,
      { states: "active" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("setContainerInfos sends one request per key", () => {
    const postSpy = jest.spyOn(http, "post").mockReturnValue(of({}) as any);
    containerService.setContainerInfos("cI", { k1: "v1", k2: "v2" });
    expect(postSpy).toHaveBeenCalledTimes(2);
    expect(postSpy).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cI/info/k1`,
      { value: "v1" },
      expect.objectContaining({ headers: expect.anything() })
    );
    expect(postSpy).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cI/info/k2`,
      { value: "v2" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("toggleAll calls tokenService for non-active, non-revoked tokens", async () => {
    const details: ContainerDetails = {
      count: 1,
      containers: [
        {
          serial: "c1",
          realms: [],
          states: [],
          tokens: [
            { serial: "t1", active: false, revoked: false } as any,
            { serial: "t2", active: false, revoked: true } as any,
            { serial: "t3", active: true, revoked: false } as any
          ],
          type: "",
          users: []
        }
      ]
    };
    containerService.containerDetail.set(details);

    const res = await lastValueFrom(containerService.toggleAll("activate"));

    expect(tokenService.toggleActive).toHaveBeenCalledTimes(1);
    expect(tokenService.toggleActive).toHaveBeenCalledWith("t1", false);

    expect(res?.length).toBe(2);
    expect(res?.filter(Boolean).length).toBe(1);
    expect(res?.[1]).toBeNull();
  });

  it("toggleAll returns null when no token matches", async () => {
    notificationService.openSnackBar.mockClear();
    const details: ContainerDetails = {
      count: 1,
      containers: [
        {
          serial: "cY",
          realms: [],
          states: [],
          tokens: [{ serial: "t4", active: true, revoked: false } as any],
          type: "",
          users: []
        }
      ]
    };
    containerService.containerDetail.set(details);
    const r = await lastValueFrom(containerService.toggleAll("activate"));
    expect(r).toBeNull();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("No tokens for action.");
  });

  it("removeAll posts combined serial list", async () => {
    const postSpy = jest.spyOn(http, "post").mockReturnValue(of({ result: true }) as any);
    const details: ContainerDetails = {
      count: 1,
      containers: [
        {
          serial: "c3",
          realms: [],
          states: [],
          tokens: [{ serial: "t5" } as any, { serial: "t6" } as any],
          type: "",
          users: []
        }
      ]
    };
    containerService.containerDetail.set(details);
    const r = await lastValueFrom(containerService.removeAll("c3"));
    expect(r?.result).toBeTruthy();
    expect(postSpy).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c3/removeall`,
      { serial: "t5,t6" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("deleteContainer sends DELETE", async () => {
    const delSpy = jest.spyOn(http, "delete").mockReturnValue(of({}) as any);
    await lastValueFrom(containerService.deleteContainer("cDel"));
    expect(delSpy).toHaveBeenCalledWith(`${containerService.containerBaseUrl}cDel`, {
      headers: expect.anything()
    });
  });

  it("createContainer posts data and returns new serial", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { value: { container_serial: "CNEW" } } } as any));
    const r = await lastValueFrom(
      containerService.createContainer({
        container_type: "generic",
        description: "d"
      })
    );
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}init`,
      {
        type: "generic",
        description: "d",
        user: undefined,
        realm: undefined,
        template: undefined,
        options: undefined
      },
      expect.objectContaining({ headers: expect.anything() })
    );
    expect(r.result?.value?.container_serial).toBe("CNEW");
  });

  it("registerContainer posts registration payload", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { value: { container_url: "u" } } } as any));
    const r = await lastValueFrom(
      containerService.registerContainer({
        container_serial: "cReg",
        passphrase_user: false,
        passphrase_prompt: "p?",
        passphrase_response: "r!"
      })
    );
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}register/initialize`,
      {
        container_serial: "cReg",
        passphrase_user: false,
        passphrase_prompt: "p?",
        passphrase_response: "r!"
      },
      expect.objectContaining({ headers: expect.anything() })
    );
    expect(r.result?.value?.container_url).toBe("u");
  });

  it("poll container details completes when state == registered", async () => {
    jest.useFakeTimers();
    contentService.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
    containerService.containerSerial.set("SMPH1");

    const getContainerSpy = jest.spyOn(http, "get").mockReturnValue(of({
      result: {
        value: {
          containers: [{ info: { registration_state: "registered" } }]
        }
      }
    } as any));

    containerService.startPolling("SMPH1");
    // Flush microtasks to allow signals/effects to propagate
    await Promise.resolve();
    jest.runAllTimers();

    expect(getContainerSpy).toHaveBeenCalled();
    expect(containerService.containerDetailResource.value()?.result?.value?.containers[0].info.registration_state).toBe("registered");
    expect(containerService.isPollingActive()).toBe(false);

    jest.useRealTimers();
  });

  it("filterParams converts blank values and drops unknown keys", () => {
    containerService.containerFilter.set(new FilterValue({ value: "user: Alice type: foo: bar" }));
    const fp = containerService.filterParams();
    expect(fp).toEqual({ user: "Alice", type: "*" });
  });

  it("pageSize falls back to 10 for invalid eventPageSize", () => {
    containerService.eventPageSize = 7;
    containerService.containerFilter.set(new FilterValue());
    expect(containerService.pageSize()).toBe(10);
  });

  it("pageSize keeps valid eventPageSize", () => {
    containerService.eventPageSize = 15;
    containerService.containerFilter.set(new FilterValue());
    expect(containerService.pageSize()).toBe(15);
  });

  it("pageIndex resets to 0 when filter changes", () => {
    containerService.pageIndex.set(2);
    expect(containerService.pageIndex()).toBe(2);
    containerService.containerFilter.set(new FilterValue({ value: "type: x" }));
    expect(containerService.pageIndex()).toBe(0);
  });

  it("filteredContainerOptions respects selectedContainer filter", () => {
    containerService.containerOptions.set(["Alpha", "Serial42", "Beta"]);
    containerService.selectedContainer.set("se");
    expect(containerService.filteredContainerOptions()).toEqual(["Serial42"]);
  });

  it("containerTypeOptions maps API result", () => {
    jest.spyOn(containerService.containerTypesResource, "value").mockReturnValue({
      result: {
        value: {
          generic: { description: "Generic", token_types: ["hmac"] }
        }
      }
    } as any);
    const opt = containerService.containerTypeOptions();
    expect(opt[0]).toEqual({
      containerType: "generic",
      description: "Generic",
      token_types: ["hmac"]
    });
  });

  it("containerDetail falls back to default when resource empty", () => {
    expect(containerService.containerDetail()).toEqual({
      containers: [],
      count: 0
    });
  });

  it("removeAll returns null when no tokens array", async () => {
    notificationService.openSnackBar.mockClear();
    containerService.containerDetail.set({
      count: 1,
      containers: [{} as any]
    });
    const r = await lastValueFrom(containerService.removeAll("cX"));
    expect(r).toBeNull();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("No valid tokens array found in data.");
  });

  it("toggleAll returns null when containerDetail invalid", async () => {
    notificationService.openSnackBar.mockClear();
    containerService.containerDetail.set({
      count: 1,
      containers: [{} as any]
    });
    const r = await lastValueFrom(containerService.toggleAll("activate"));
    expect(r).toBeNull();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("No valid tokens array found in data.");
  });

  it("filterParams handles wildcards and converts blank values", () => {
    (containerService.apiFilter as string[]).push("desc");
    containerService.containerFilter.set(new FilterValue({ value: "desc: foo token_serial: 123 type: user: Bob" }));
    expect(containerService.filterParams()).toEqual({
      desc: "*foo*",
      token_serial: "123",
      type: "*",
      user: "Bob"
    });
  });

  it("pageIndex resets when pageSize source changes", () => {
    containerService.pageIndex.set(4);
    containerService.eventPageSize = 5;
    containerService.containerFilter.set(new FilterValue());
    expect(containerService.pageSize()).toBe(5);
    expect(containerService.pageIndex()).toBe(0);
  });

  it("toggleActive switches disabled → active", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { active: true } } as any));
    await lastValueFrom(containerService.toggleActive("cD", ["disabled"]));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cD/states`,
      { states: "active" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("removeToken posts payload & propagates errors", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: true } as any));
    await lastValueFrom(containerService.removeToken("tok1", "cont1"));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cont1/remove`,
      { serial: "tok1" },
      expect.objectContaining({ headers: expect.anything() })
    );

    jest.spyOn(http, "post").mockReturnValueOnce(throwError(() => ({ status: 500, error: {} })));
    await expect(lastValueFrom(containerService.removeToken("tokX", "contX"))).rejects.toBeDefined();
    expect(notificationService.openSnackBar).toHaveBeenCalled();
  });

  it("setContainerRealm joins array, blank array ⇒ \"\"", async () => {
    const post = jest.spyOn(http, "post").mockReturnValue(of({}) as any);
    await lastValueFrom(containerService.setContainerRealm("cX", ["r1", "r2"]));
    expect(post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cX/realms`,
      { realms: "r1,r2" },
      expect.objectContaining({ headers: expect.anything() })
    );

    await lastValueFrom(containerService.setContainerRealm("cX", []));
    expect(post).toHaveBeenLastCalledWith(
      `${containerService.containerBaseUrl}cX/realms`,
      { realms: "" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("toggleActive adds active when neither active nor disabled present", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { active: true } } as any));
    await lastValueFrom(containerService.toggleActive("c7", ["locked"]));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c7/states`,
      { states: "locked,active" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("toggleAll deactivates active tokens", async () => {
    containerService.containerDetail.set({
      count: 1,
      containers: [
        {
          serial: "c8",
          realms: [],
          states: [],
          tokens: [
            { serial: "tOn", active: true, revoked: false } as any,
            { serial: "tOff", active: false, revoked: false } as any
          ],
          type: "",
          users: []
        }
      ]
    });
    await lastValueFrom(containerService.toggleAll("deactivate"));
    expect(tokenService.toggleActive).toHaveBeenCalledWith("tOn", true);
  });

  it("removeAll early-returns when tokens array empty", async () => {
    notificationService.openSnackBar.mockClear();
    containerService.containerDetail.set({
      count: 1,
      containers: [{ serial: "c9", tokens: [] } as any]
    });
    const res = await lastValueFrom(containerService.removeAll("c9"));
    expect(res).toBeNull();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("No tokens to remove.");
  });

  it("filterParams wildcards non-ID fields", () => {
    containerService.containerFilter.set(new FilterValue({ value: "container_serial: S1 desc: foo" }));
    expect(containerService.filterParams()).toEqual({
      container_serial: "S1",
      desc: "*foo*"
    });
  });

  it("pageSize boundary values 5 and 15 are respected", () => {
    containerService.eventPageSize = 5;
    containerService.containerFilter.set(new FilterValue());
    expect(containerService.pageSize()).toBe(5);

    containerService.eventPageSize = 15;
    containerService.containerFilter.set(new FilterValue());
    expect(containerService.pageSize()).toBe(15);
  });

  it("containerTypeOptions returns [] when API empty", () => {
    jest.spyOn(containerService.containerTypesResource, "value").mockReturnValue(undefined as any);
    expect(containerService.containerTypeOptions()).toEqual([]);
  });

  // === FIX 1: setContainerDescription — loosen header equality and assert Authorization optionally ===
  it("setContainerDescription posts payload (robust headers assertion)", async () => {
    const post = jest.spyOn(http, "post").mockReturnValue(of({}) as any);
    await lastValueFrom(containerService.setContainerDescription("cD", "desc"));

    const expectedUrl = `${containerService.containerBaseUrl}cD/description`;
    expect(post).toHaveBeenCalledWith(
      expectedUrl,
      { description: "desc" },
      expect.objectContaining({ headers: expect.anything() })
    );

    // Optional: verify Authorization header value regardless of HttpHeaders vs. plain object
    const hdrs = (post as jest.Mock).mock.calls[0][2]?.headers;
    const authHeader = typeof hdrs?.get === "function" ? hdrs.get("Authorization") : hdrs?.Authorization;
    expect(authHeader).toMatch(/^Bearer /);
  });

  // === Extra small coverage to close error branches cleanly ===
  it("addTokenToContainer/ removeTokenFromContainer / assignUser / unassignUser error paths surface snackbar", async () => {
    jest.spyOn(http, "post")
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 }))) // addTokenToContainer
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 }))) // removeTokenFromContainer
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 }))) // assignUser
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 }))); // unassignUser

    await expect(lastValueFrom(containerService.addTokenToContainer("c", "t"))).rejects.toBeDefined();
    await expect(lastValueFrom(containerService.removeTokenFromContainer("c", "t"))).rejects.toBeDefined();
    await expect(lastValueFrom(containerService.assignUser({ containerSerial: "c", username: "u", userRealm: "r" })))
      .rejects.toBeDefined();
    await expect(lastValueFrom(containerService.unassignUser("c", "u", "r"))).rejects.toBeDefined();

    expect(notificationService.openSnackBar).toHaveBeenCalledTimes(4);
  });

  it("deleteInfo / deleteAllTokens error paths surface snackbar", async () => {
    jest.spyOn(http, "delete").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 404 })));
    await expect(lastValueFrom(containerService.deleteInfo("c", "k"))).rejects.toBeDefined();

    jest.spyOn(http, "post").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));
    await expect(lastValueFrom(containerService.deleteAllTokens({ containerSerial: "c", serialList: "a,b" })))
      .rejects.toBeDefined();

    expect(notificationService.openSnackBar).toHaveBeenCalledTimes(2);
  });

  it("registerContainer / toggleActive error paths surface snackbar", async () => {
    jest.spyOn(http, "post")
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 400 }))) // register
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 }))); // toggleActive

    await expect(lastValueFrom(containerService.registerContainer({
      container_serial: "c",
      passphrase_user: false,
      passphrase_prompt: "p",
      passphrase_response: "r"
    }))).rejects.toBeDefined();

    await expect(lastValueFrom(containerService.toggleActive("c", ["active"]))).rejects.toBeDefined();

    expect(notificationService.openSnackBar).toHaveBeenCalledTimes(2);
  });

  it("setContainerInfos: per-key error surfaces snackbar", async () => {
    const post = jest.spyOn(http, "post")
      .mockReturnValueOnce(of({}) as any) // k1 ok
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 }))); // k2 fails

    const [o1, o2] = containerService.setContainerInfos("cI", { k1: "v1", k2: "v2" });
    await lastValueFrom(o1);
    await expect(lastValueFrom(o2)).rejects.toBeDefined();

    expect(post).toHaveBeenNthCalledWith(
      1,
      `${containerService.containerBaseUrl}cI/info/k1`,
      { value: "v1" },
      expect.objectContaining({ headers: expect.anything() })
    );
    expect(post).toHaveBeenNthCalledWith(
      2,
      `${containerService.containerBaseUrl}cI/info/k2`,
      { value: "v2" },
      expect.objectContaining({ headers: expect.anything() })
    );
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Failed to save container infos.")
    );
  });

  it("deleteContainer error surfaces snackbar", async () => {
    jest.spyOn(http, "delete").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));
    await expect(lastValueFrom(containerService.deleteContainer("cDelErr"))).rejects.toBeDefined();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Failed to delete container.")
    );
  });

  it("unregister posts to the correct endpoint and returns result", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: { value: { container_serial: "CONT1234" } } } as any));
    const r = await lastValueFrom(containerService.unregister("CONT1234"));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}register/CONT1234/terminate`,
      {},
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("unregister error surfaces snackbar", async () => {
    jest.spyOn(http, "post").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));
    await expect(lastValueFrom(containerService.unregister("CONT1234"))).rejects.toBeDefined();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining("Failed to unregister container.")
    );
  });
});
