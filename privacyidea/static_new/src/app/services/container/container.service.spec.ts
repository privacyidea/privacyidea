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

import { HttpClient, HttpErrorResponse, provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { signal, WritableSignal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuthService } from "@services/auth/auth.service";
import {
  ContainerCreateResult,
  ContainerDetailData,
  ContainerDetails,
  ContainerDetailToken,
  ContainerRegisterData,
  ContainerService,
  ContainerType,
  TemplateComparisonResult,
  toWildcardParam
} from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService, Tokens } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import {
  MockAuthService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { lastValueFrom, of, throwError } from "rxjs";

describe("ContainerService", () => {
  let containerService: ContainerService;
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let authServiceMock: MockAuthService;
  let notificationServiceMock: MockNotificationService;
  let tokenServiceMock: MockTokenService;
  let contentServiceMock: MockContentService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ContainerService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: UserService, useClass: MockUserService },
        MockLocalService,
        MockNotificationService
      ]
    });
    containerService = TestBed.inject(ContainerService);
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  it("creates the service", () => {
    expect(containerService).toBeTruthy();
  });

  it("assignContainer posts payload and returns result", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: true } as unknown as PiResponse<boolean>));
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
    expect(notificationServiceMock.error).toHaveBeenCalled();
  });

  it("toggleActive switches active → disabled", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValue(of({ result: { disabled: true } } as unknown as PiResponse<{ disabled: boolean }>));
    await lastValueFrom(containerService.toggleActive("c1", ["active"]));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c1/states`,
      { states: "disabled" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("toggleActive adds active when no state present", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValue(of({ result: { active: true } } as unknown as PiResponse<{ active: boolean }>));
    await lastValueFrom(containerService.toggleActive("c2", []));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c2/states`,
      { states: "active" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("setContainerInfos sends one request per key", () => {
    const postSpy = jest.spyOn(http, "post").mockReturnValue(of({}));
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
            { serial: "t1", active: false, revoked: false } as unknown as ContainerDetailToken,
            { serial: "t2", active: false, revoked: true } as unknown as ContainerDetailToken,
            { serial: "t3", active: true, revoked: false } as unknown as ContainerDetailToken
          ],
          type: "",
          users: []
        }
      ]
    };
    containerService.containerDetails.set(details);

    const res = await lastValueFrom(containerService.toggleAll("activate"));

    expect(tokenServiceMock.toggleActive).toHaveBeenCalledTimes(1);
    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("t1", false);

    expect(res?.length).toBe(2);
    expect(res?.filter(Boolean).length).toBe(1);
    expect(res?.[1]).toBeNull();
  });

  it("toggleAll returns null when no token matches", async () => {
    notificationServiceMock.warning.mockClear();
    const details: ContainerDetails = {
      count: 1,
      containers: [
        {
          serial: "cY",
          realms: [],
          states: [],
          tokens: [{ serial: "t4", active: true, revoked: false } as unknown as ContainerDetailToken],
          type: "",
          users: []
        }
      ]
    };
    containerService.containerDetails.set(details);
    const r = await lastValueFrom(containerService.toggleAll("activate"));
    expect(r).toBeNull();
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("No tokens for action.");
  });

  it("removeAll posts combined serial list", async () => {
    const postSpy = jest.spyOn(http, "post").mockReturnValue(of({ result: true } as unknown as PiResponse<boolean>));
    const details: ContainerDetails = {
      count: 1,
      containers: [
        {
          serial: "c3",
          realms: [],
          states: [],
          tokens: [
            { serial: "t5" } as unknown as ContainerDetailToken,
            { serial: "t6" } as unknown as ContainerDetailToken
          ],
          type: "",
          users: []
        }
      ]
    };
    containerService.containerDetails.set(details);
    const r = await lastValueFrom(containerService.removeAll("c3"));
    expect(r?.result).toBeTruthy();
    expect(postSpy).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c3/removeall`,
      { serial: "t5,t6" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("deleteContainer sends DELETE", async () => {
    const delSpy = jest.spyOn(http, "delete").mockReturnValue(of({}));
    await lastValueFrom(containerService.deleteContainer("cDel"));
    expect(delSpy).toHaveBeenCalledWith(`${containerService.containerBaseUrl}cDel`, {
      headers: expect.anything()
    });
  });

  it("createContainer posts data and returns new serial", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValue(
        of({ result: { value: { container_serial: "CNEW" } } } as unknown as PiResponse<ContainerCreateResult>)
      );
    const r = await lastValueFrom(
      containerService.createContainer({
        type: "generic",
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
    jest
      .spyOn(http, "post")
      .mockReturnValue(
        of({ result: { value: { container_url: "u" } } } as unknown as PiResponse<ContainerRegisterData>)
      );
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

  it("poll container details completes when state == registered for container create", async () => {
    contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS_CREATE);
    containerService.containerSerial.set("SMPH1");

    const valueSpy = jest
      .spyOn(containerService.containerDetailsResource, "value")
      .mockReturnValueOnce(undefined)
      .mockReturnValue({
        result: {
          value: {
            count: 1,
            containers: [{ info: { registration_state: "registered" } }]
          }
        }
      } as unknown as PiResponse<ContainerDetails>);
    jest.spyOn(containerService.containerDetailsResource, "hasValue").mockReturnValue(true);

    containerService.startPolling("SMPH1");
    TestBed.tick();
    const pollingTrigger = (containerService as unknown as { pollingTrigger: WritableSignal<number> }).pollingTrigger;
    pollingTrigger.update((n) => n + 1);
    TestBed.tick();

    expect(valueSpy).toHaveBeenCalled();
    expect(
      containerService.containerDetailsResource.value()?.result?.value?.containers[0].info?.registration_state
    ).toBe("registered");
    expect(containerService.isPollingActive()).toBe(false);
    expect(notificationServiceMock.warning).not.toHaveBeenCalled();
  });

  it("stopPolling resets isPollingActive", () => {
    containerService.startPolling("SMPH1");
    expect(containerService.isPollingActive()).toBe(true);

    containerService.stopPolling();
    expect(containerService.isPollingActive()).toBe(false);
  });

  it("poll container details completes when state == registered for container details", () => {
    contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS_DETAILS + "/SMPH1");
    containerService.containerSerial.set("SMPH1");

    const valueSpy = jest
      .spyOn(containerService.containerDetailsResource, "value")
      .mockReturnValueOnce(undefined)
      .mockReturnValue({
        result: {
          value: {
            count: 1,
            containers: [{ info: { registration_state: "registered" } }]
          }
        }
      } as unknown as PiResponse<ContainerDetails>);
    jest.spyOn(containerService.containerDetailsResource, "hasValue").mockReturnValue(true);

    containerService.startPolling("SMPH1");
    TestBed.tick();
    const pollingTrigger = (containerService as unknown as { pollingTrigger: WritableSignal<number> }).pollingTrigger;
    pollingTrigger.update((n) => n + 1);
    TestBed.tick();

    expect(valueSpy).toHaveBeenCalled();
    expect(
      containerService.containerDetailsResource.value()?.result?.value?.containers[0].info?.registration_state
    ).toBe("registered");
    expect(containerService.isPollingActive()).toBe(false);
    expect(notificationServiceMock.success).toHaveBeenCalledWith("Container registered successfully.");
  });

  it("startPolling returns early when already active", () => {
    contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS_DETAILS + "/SMPH1");
    jest.spyOn(containerService.containerDetailsResource, "hasValue").mockReturnValue(true);
    jest.spyOn(containerService.containerDetailsResource, "value").mockReturnValue({
      result: { value: { count: 1, containers: [{ info: { registration_state: "pending" } }] } }
    } as unknown as PiResponse<ContainerDetails>);

    containerService.startPolling("SMPH1");
    expect(containerService.isPollingActive()).toBe(true);

    const pollingTrigger = (containerService as unknown as { pollingTrigger: WritableSignal<number> }).pollingTrigger;
    const triggerBefore = pollingTrigger();
    containerService.startPolling("SMPH2");

    expect(pollingTrigger()).toBe(triggerBefore);
    expect(containerService.containerSerial()).toBe("SMPH1");
  });

  it("poll container details shows rollover success notification when isRollover is true", () => {
    contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS_DETAILS + "/SMPH1");
    containerService.containerSerial.set("SMPH1");

    jest
      .spyOn(containerService.containerDetailsResource, "value")
      .mockReturnValueOnce(undefined)
      .mockReturnValue({
        result: {
          value: {
            count: 1,
            containers: [{ info: { registration_state: "registered" } }]
          }
        }
      } as unknown as PiResponse<ContainerDetails>);
    jest.spyOn(containerService.containerDetailsResource, "hasValue").mockReturnValue(true);

    containerService.startPolling("SMPH1", true);
    TestBed.tick();
    const pollingTrigger = (containerService as unknown as { pollingTrigger: WritableSignal<number> }).pollingTrigger;
    pollingTrigger.update((n) => n + 1);
    TestBed.tick();

    expect(containerService.isPollingActive()).toBe(false);
    expect(notificationServiceMock.success).toHaveBeenCalledWith("Container rollover completed successfully.");
  });

  it("filterParams converts blank values and drops unknown keys", () => {
    containerService.containerFilter.set(new FilterValue({ value: "type: generic description: foo: bar" }));
    const filterParams = containerService.filterParams();
    expect(filterParams).toEqual({ type: "generic" });
  });

  it("filterParams maps a single type to the scalar `type` param", () => {
    containerService.containerFilter.set(new FilterValue({ value: "type: smartphone" }));
    expect(containerService.filterParams()).toEqual({ type: "smartphone" });
  });

  it("filterParams preserves `*` wildcards on a single type", () => {
    containerService.containerFilter.set(new FilterValue({ value: "type: smart*" }));
    expect(containerService.filterParams()).toEqual({ type: "smart*" });
  });

  it("filterParams maps multiple comma-separated types to `type_list`", () => {
    containerService.containerFilter.set(new FilterValue({ value: "type: smartphone,yubikey" }));
    expect(containerService.filterParams()).toEqual({ type_list: "smartphone,yubikey" });
  });

  it("filterParams trims whitespace and de-duplicates the type list", () => {
    containerService.containerFilter.set(new FilterValue({ value: "type: ' smartphone , yubikey , smartphone '" }));
    expect(containerService.filterParams()).toEqual({ type_list: "smartphone,yubikey" });
  });

  it("filterParams accepts `types` as a synonym for `type` (single)", () => {
    containerService.containerFilter.set(new FilterValue({ value: "types: generic" }));
    expect(containerService.filterParams()).toEqual({ type: "generic" });
  });

  it("filterParams accepts `types` as a synonym for `type` (multiple)", () => {
    containerService.containerFilter.set(new FilterValue({ value: "types: smartphone,yubikey" }));
    expect(containerService.filterParams()).toEqual({ type_list: "smartphone,yubikey" });
  });

  it("filterParams merges `type` and `types` values into a single type_list", () => {
    containerService.containerFilter.set(new FilterValue({ value: "type: smartphone types: yubikey" }));
    expect(containerService.filterParams()).toEqual({ type_list: "smartphone,yubikey" });
  });

  it("pageSize falls back to 10 for invalid eventPageSize", () => {
    containerService.eventPageSize.set(-1);
    expect(containerService.pageSize()).toBe(10);
  });

  it("pageSize keeps valid eventPageSize", () => {
    containerService.eventPageSize.set(15);
    expect(containerService.pageSize()).toBe(15);
  });

  it("pageIndex resets to 0 when filter changes", () => {
    containerService.pageIndex.set(2);
    expect(containerService.pageIndex()).toBe(2);
    containerService.containerFilter.set(new FilterValue({ value: "type: x" }));
    expect(containerService.pageIndex()).toBe(0);
  });

  it("removeAll returns null when no tokens array", async () => {
    notificationServiceMock.warning.mockClear();
    containerService.containerDetails.set({
      count: 1,
      containers: [{} as unknown as ContainerDetailData]
    });
    const r = await lastValueFrom(containerService.removeAll("cX"));
    expect(r).toBeNull();
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("No valid tokens array found in data.");
  });

  it("toggleAll returns null when containerDetails invalid", async () => {
    notificationServiceMock.warning.mockClear();
    containerService.containerDetails.set({
      count: 1,
      containers: [{} as unknown as ContainerDetailData]
    });
    const r = await lastValueFrom(containerService.toggleAll("activate"));
    expect(r).toBeNull();
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("No valid tokens array found in data.");
  });

  it("filterParams handles wildcards and converts blank values", () => {
    (containerService.apiFilter as string[]).push("desc");
    containerService.containerFilter.set(new FilterValue({ value: "desc: foo token_serial: 123 type: user: Bob" }));
    expect(containerService.filterParams()).toEqual({
      desc: "*foo*",
      token_serial: "*123*"
    });
  });

  it("pageIndex resets when pageSize source changes", () => {
    containerService.pageIndex.set(4);
    containerService.eventPageSize.set(5);
    expect(containerService.pageSize()).toBe(5);
    expect(containerService.pageIndex()).toBe(0);
  });

  it("toggleActive switches disabled → active", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValue(of({ result: { active: true } } as unknown as PiResponse<{ active: boolean }>));
    await lastValueFrom(containerService.toggleActive("cD", ["disabled"]));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cD/states`,
      { states: "active" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("removeToken posts payload & propagates errors", async () => {
    jest.spyOn(http, "post").mockReturnValue(of({ result: true } as unknown as PiResponse<boolean>));
    await lastValueFrom(containerService.removeToken("tok1", "cont1"));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}cont1/remove`,
      { serial: "tok1" },
      expect.objectContaining({ headers: expect.anything() })
    );

    jest.spyOn(http, "post").mockReturnValueOnce(throwError(() => ({ status: 500, error: {} })));
    await expect(lastValueFrom(containerService.removeToken("tokX", "contX"))).rejects.toBeDefined();
    expect(notificationServiceMock.error).toHaveBeenCalled();
  });

  it('setContainerRealm joins array, blank array ⇒ ""', async () => {
    const post = jest.spyOn(http, "post").mockReturnValue(of({}));
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
    jest
      .spyOn(http, "post")
      .mockReturnValue(of({ result: { active: true } } as unknown as PiResponse<{ active: boolean }>));
    await lastValueFrom(containerService.toggleActive("c7", ["locked"]));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}c7/states`,
      { states: "locked,active" },
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("toggleAll deactivates active tokens", async () => {
    containerService.containerDetails.set({
      count: 1,
      containers: [
        {
          serial: "c8",
          realms: [],
          states: [],
          tokens: [
            { serial: "tOn", active: true, revoked: false } as unknown as ContainerDetailToken,
            { serial: "tOff", active: false, revoked: false } as unknown as ContainerDetailToken
          ],
          type: "",
          users: []
        }
      ]
    });
    await lastValueFrom(containerService.toggleAll("deactivate"));
    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("tOn", true);
  });

  it("removeAll early-returns when tokens array empty", async () => {
    notificationServiceMock.warning.mockClear();
    containerService.containerDetails.set({
      count: 1,
      containers: [{ serial: "c9", tokens: [] } as unknown as ContainerDetailData]
    });
    const res = await lastValueFrom(containerService.removeAll("c9"));
    expect(res).toBeNull();
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("No tokens to remove.");
  });

  it("filterParams wildcards non-ID fields", () => {
    containerService.containerFilter.set(new FilterValue({ value: "container_serial: S1 desc: foo" }));
    expect(containerService.filterParams()).toEqual({
      container_serial: "*S1*",
      desc: "*foo*"
    });
  });

  it("pageSize boundary values 5 and 15 are respected", () => {
    containerService.eventPageSize.set(5);
    expect(containerService.pageSize()).toBe(5);

    containerService.eventPageSize.set(15);
    expect(containerService.pageSize()).toBe(15);
  });

  it("setContainerDescription posts payload (robust headers assertion)", async () => {
    authServiceMock.getHeaders.mockReturnValueOnce({ Authorization: "Bearer token mock" });
    const post = jest.spyOn(http, "post").mockReturnValue(of({}));
    await lastValueFrom(containerService.setContainerDescription("cD", "desc"));

    const expectedUrl = `${containerService.containerBaseUrl}cD/description`;
    expect(post).toHaveBeenCalledWith(
      expectedUrl,
      { description: "desc" },
      expect.objectContaining({ headers: expect.anything() })
    );

    const hdrs = (post as jest.Mock).mock.calls[0][2]?.headers;
    const authHeader = typeof hdrs?.get === "function" ? hdrs.get("Authorization") : hdrs?.Authorization;
    expect(authHeader).toMatch(/^Bearer /);
  });

  it("addTokenToContainer/ removeTokenFromContainer / assignUser / unassignUser error paths surface snackbar", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })))
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })))
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })))
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));

    await expect(lastValueFrom(containerService.addTokenToContainer("c", "t"))).rejects.toBeDefined();
    await expect(lastValueFrom(containerService.removeTokenFromContainer("c", "t"))).rejects.toBeDefined();
    await expect(
      lastValueFrom(containerService.assignUser({ containerSerial: "c", username: "u", userRealm: "r" }))
    ).rejects.toBeDefined();
    await expect(lastValueFrom(containerService.unassignUser("c", "u", "r"))).rejects.toBeDefined();

    expect(notificationServiceMock.error).toHaveBeenCalledTimes(4);
  });

  it("deleteInfo / deleteAllTokens error paths surface snackbar", async () => {
    jest.spyOn(http, "delete").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 404 })));
    await expect(lastValueFrom(containerService.deleteInfo("c", "k"))).rejects.toBeDefined();

    jest.spyOn(http, "post").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));
    await expect(
      lastValueFrom(containerService.deleteAllTokens({ containerSerial: "c", serialList: "a,b" }))
    ).rejects.toBeDefined();

    expect(notificationServiceMock.error).toHaveBeenCalledTimes(2);
  });

  it("registerContainer / toggleActive error paths surface snackbar", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 400 })))
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));

    await expect(
      lastValueFrom(
        containerService.registerContainer({
          container_serial: "c",
          passphrase_user: false,
          passphrase_prompt: "p",
          passphrase_response: "r"
        })
      )
    ).rejects.toBeDefined();

    await expect(lastValueFrom(containerService.toggleActive("c", ["active"]))).rejects.toBeDefined();

    expect(notificationServiceMock.error).toHaveBeenCalledTimes(2);
  });

  it("setContainerInfos: per-key error surfaces snackbar", async () => {
    const post = jest
      .spyOn(http, "post")
      .mockReturnValueOnce(of({}))
      .mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));

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
    expect(notificationServiceMock.error).toHaveBeenCalledWith(
      expect.stringContaining("Failed to save container infos.")
    );
  });

  it("deleteContainer error surfaces snackbar", async () => {
    jest.spyOn(http, "delete").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));
    await expect(lastValueFrom(containerService.deleteContainer("cDelErr"))).rejects.toBeDefined();
    expect(notificationServiceMock.error).toHaveBeenCalledWith(expect.stringContaining("Failed to delete container."));
  });

  it("unregister posts to the correct endpoint and returns result", async () => {
    jest
      .spyOn(http, "post")
      .mockReturnValue(
        of({ result: { value: { container_serial: "CONT/1234" } } } as unknown as PiResponse<ContainerCreateResult>)
      );
    await lastValueFrom(containerService.unregister("CONT/1234"));
    expect(http.post).toHaveBeenCalledWith(
      `${containerService.containerBaseUrl}register/${encodeURIComponent("CONT/1234")}/terminate`,
      {},
      expect.objectContaining({ headers: expect.anything() })
    );
  });

  it("unregister error surfaces snackbar", async () => {
    jest.spyOn(http, "post").mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 500 })));
    await expect(lastValueFrom(containerService.unregister("CONT1234"))).rejects.toBeDefined();
    expect(notificationServiceMock.error).toHaveBeenCalledWith(
      expect.stringContaining("Failed to unregister container.")
    );
  });

  it("should not include empty filter values in filterParams", () => {
    containerService.containerFilter.set({
      filterMap: new Map([
        ["container_serial", ""],
        ["type", "generic"],
        ["user", "   "],
        ["token_serial", "*"]
      ])
    } as unknown as FilterValue);

    const params = containerService.filterParams();
    expect(params).not.toHaveProperty("container_serial");
    expect(params).toHaveProperty("type", "generic");
    expect(params).not.toHaveProperty("user");
    expect(params).not.toHaveProperty("token_serial");
  });

  describe("containerTypeOptions", () => {
    it("containerTypeOptions returns [] when API empty", () => {
      jest.spyOn(containerService.containerTypesResource, "value").mockReturnValue(undefined);
      expect(containerService.containerTypeOptions()).toEqual([]);
    });

    it("should update containerTypeOptions from containerTypesResource", async () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/container/types");
      expect(req.request.method).toBe("GET");
      req.flush(
        MockPiResponse.fromValue({
          typeA: { description: "Type A", token_types: ["tt1", "tt2"] },
          typeB: { description: "Type B", token_types: ["tt2", "tt3"] }
        })
      );
      await Promise.resolve();

      expect(containerService.containerTypeOptions()).toEqual([
        { containerType: "typeA", description: "Type A", token_types: ["tt1", "tt2"] },
        { containerType: "typeB", description: "Type B", token_types: ["tt2", "tt3"] }
      ]);
    });

    it("containerTypeOptions should handle error state from containerTypesResource", async () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/container/types");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(containerService.containerTypeOptions()).toEqual([]);
    });
  });

  describe("containerDetails", () => {
    it("containerDetail falls back to default when resource empty", () => {
      expect(containerService.containerDetails()).toEqual({
        containers: [],
        count: 0
      });
    });

    it("should update containerDetail from containerDetailResource when not yet present", async () => {
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      // Set the serial so the resource will be triggered
      containerService.containerSerial.set("c1");
      TestBed.tick();

      const req = httpMock.expectOne(
        (r) => r.url === "/container/" && r.params.has("container_serial") && r.params.get("container_serial") === "c1"
      );
      expect(req.request.method).toBe("GET");
      req.flush(
        MockPiResponse.fromValue({
          count: 1,
          containers: [{ serial: "c1", type: "typeA", realms: [], states: [], tokens: [], users: [] }]
        })
      );
      await Promise.resolve();

      expect(containerService.containerDetails()).toEqual({
        count: 1,
        containers: [{ serial: "c1", type: "typeA", realms: [], states: [], tokens: [], users: [] }]
      });
    });

    it("should handle error state from containerDetailResource", async () => {
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      containerService.containerSerial.set("c2");
      TestBed.tick();

      const req = httpMock.expectOne(
        (r) => r.url === "/container/" && r.params.has("container_serial") && r.params.get("container_serial") === "c2"
      );
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(containerService.containerDetails()).toEqual({ containers: [], count: 0 });
    });

    it("should reset to default when containerDetailResource errors after successful load", async () => {
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      containerService.containerSerial.set("c1");
      TestBed.tick();

      let req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("container_serial") === "c1");
      req.flush(
        MockPiResponse.fromValue({
          count: 1,
          containers: [{ serial: "c1", type: "typeA", realms: [], states: [], tokens: [], users: [] }]
        })
      );
      await Promise.resolve();
      expect(containerService.containerDetails().count).toBe(1);

      containerService.containerDetailsResource.reload();
      TestBed.tick();
      req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("container_serial") === "c1");
      req.flush("Error", { status: 500, statusText: "Server Error" });
      await Promise.resolve();

      expect(containerService.containerDetails()).toEqual({ containers: [], count: 0 });
    });
  });

  describe("compatibleTypes and containersForTokenType", () => {
    let containerTypeOptionsSignal: WritableSignal<ContainerType[]>;
    let compatibleWithSelectedTokenTypeSignal: WritableSignal<string>;

    beforeEach(() => {
      // Use Angular signals for mocking
      containerTypeOptionsSignal = signal([
        { containerType: "typeA", description: "Type A", token_types: ["tt1", "tt2"] },
        { containerType: "typeB", description: "Type B", token_types: ["tt2", "tt3"] },
        { containerType: "typeC", description: "Type C", token_types: ["tt3"] }
      ]);
      compatibleWithSelectedTokenTypeSignal = signal("tt2");
      const mockableService = containerService as unknown as {
        containerTypeOptions: WritableSignal<ContainerType[]>;
        compatibleWithSelectedTokenType: WritableSignal<string>;
      };
      mockableService.containerTypeOptions = containerTypeOptionsSignal;
      mockableService.compatibleWithSelectedTokenType = compatibleWithSelectedTokenTypeSignal;

      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
    });

    it("should compute compatibleTypes correctly", () => {
      expect(containerService["compatibleTypes"]()).toEqual(["typeA", "typeB"]);
    });

    it("sends the full list of compatible types as a comma-separated `type` param and returns the serials the backend returned", async () => {
      TestBed.tick();

      const req = httpMock.expectOne(
        (r) => r.url === "/container/" && r.params.get("no_token") === "1" && r.params.get("type") === "typeA,typeB"
      );
      expect(req.request.method).toBe("GET");
      req.flush(
        MockPiResponse.fromValue({
          containers: [
            { serial: "c1", type: "typeA", realms: [], states: [], tokens: [], users: [] },
            { serial: "c2", type: "typeB", realms: [], states: [], tokens: [], users: [] }
          ]
        })
      );
      await Promise.resolve();

      expect(containerService.containersForTokenType()).toEqual(["c1", "c2"]);
    });

    it("should handle containersForTokenTypeResource error", async () => {
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }));
      await Promise.resolve();

      expect(containerService.containersForTokenType()).toEqual([]);
    });

    it("should reset containersForTokenType to empty when resource errors after success", async () => {
      TestBed.tick();

      let req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      req.flush(
        MockPiResponse.fromValue({
          containers: [
            { serial: "c1", type: "typeA", realms: [], states: [], tokens: [], users: [] },
            { serial: "c2", type: "typeB", realms: [], states: [], tokens: [], users: [] }
          ]
        })
      );
      await Promise.resolve();
      expect(containerService.containersForTokenType()).toEqual(["c1", "c2"]);

      containerService.containersForTokenTypeResource.reload();
      TestBed.tick();
      req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      req.flush("Error", { status: 500, statusText: "Server Error" });
      await Promise.resolve();

      expect(containerService.containersForTokenType()).toEqual([]);
    });

    it("does not fire the request when no container type is compatible with the selected token type", () => {
      compatibleWithSelectedTokenTypeSignal.set("unknown-token-type");
      TestBed.tick();

      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      expect(containerService.containersForTokenType()).toEqual([]);
    });
  });

  describe("serialFilterParam", () => {
    it("returns empty object for null serial", () => {
      containerService.selectedContainerSerial.set(null);
      expect(
        (containerService as unknown as { serialFilterParam: () => Record<string, string> }).serialFilterParam()
      ).toEqual({});
    });

    it("returns empty object for empty string", () => {
      containerService.selectedContainerSerial.set("");
      expect(
        (containerService as unknown as { serialFilterParam: () => Record<string, string> }).serialFilterParam()
      ).toEqual({});
    });

    it("returns empty object for whitespace-only string", () => {
      containerService.selectedContainerSerial.set("  ");
      expect(
        (containerService as unknown as { serialFilterParam: () => Record<string, string> }).serialFilterParam()
      ).toEqual({});
    });

    it("wraps valid serial with wildcards", () => {
      containerService.selectedContainerSerial.set("CONT1");
      expect(
        (containerService as unknown as { serialFilterParam: () => Record<string, string> }).serialFilterParam()
      ).toEqual({ container_serial: "*CONT1*" });
    });

    it("trims whitespace before wrapping", () => {
      containerService.selectedContainerSerial.set("  CONT1  ");
      expect(
        (containerService as unknown as { serialFilterParam: () => Record<string, string> }).serialFilterParam()
      ).toEqual({ container_serial: "*CONT1*" });
    });
  });

  describe("containersForTokenTypeResource loading conditions", () => {
    let mockableService: {
      containerTypeOptions: WritableSignal<ContainerType[]>;
      compatibleWithSelectedTokenType: WritableSignal<string>;
    };

    beforeEach(() => {
      mockableService = containerService as unknown as {
        containerTypeOptions: WritableSignal<ContainerType[]>;
        compatibleWithSelectedTokenType: WritableSignal<string>;
      };
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      // Make sure compatibleTypes() is non-empty so the resource fires by default —
      // individual tests can override these signals as needed.
      mockableService.containerTypeOptions = signal([
        { containerType: "smartphone", description: "", token_types: ["push"] },
        { containerType: "generic", description: "", token_types: ["push", "hotp"] }
      ]);
      mockableService.compatibleWithSelectedTokenType = signal("push");
    });

    it("does not load on containers list route", () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      httpMock
        .match((r) => r.url === "/container/")
        .forEach((r) => r.flush(MockPiResponse.fromValue({ containers: [], count: 0 })));
    });

    it("loads on enrollment route with no_token param", async () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
      TestBed.tick();
      const req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
    });

    it("loads on token details route when token is available and not in a container", async () => {
      jest.spyOn(tokenServiceMock.tokenDetailResource, "hasValue").mockReturnValue(true);
      jest.spyOn(tokenServiceMock.tokenDetailResource, "value").mockReturnValue({
        result: { value: { tokens: [{ container_serial: "" }] } }
      } as unknown as PiResponse<Tokens>);
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_DETAILS + "SERIAL1");
      TestBed.tick();
      const req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("no_token") === "1");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
    });

    it("does not load on token details route when token is already in a container", () => {
      jest.spyOn(tokenServiceMock.tokenDetailResource, "hasValue").mockReturnValue(true);
      jest.spyOn(tokenServiceMock.tokenDetailResource, "value").mockReturnValue({
        result: { value: { tokens: [{ container_serial: "CONT-EXISTING" }] } }
      } as unknown as PiResponse<Tokens>);
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_DETAILS + "SERIAL1");
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("no_token") === "1");
    });

    it("does not load on token details route when token detail resource has no value", () => {
      jest.spyOn(tokenServiceMock.tokenDetailResource, "hasValue").mockReturnValue(false);
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_DETAILS + "SERIAL1");
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("no_token") === "1");
    });

    it("sends a single compatible type as the `type` param", async () => {
      mockableService.containerTypeOptions = signal([
        { containerType: "smartphone", description: "", token_types: ["push"] }
      ]);
      mockableService.compatibleWithSelectedTokenType = signal("push");
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
      TestBed.tick();
      const req = httpMock.expectOne(
        (r) => r.url === "/container/" && r.params.get("no_token") === "1" && r.params.get("type") === "smartphone"
      );
      req.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
    });

    it("sends multiple compatible types as a comma-separated `type` param", async () => {
      mockableService.containerTypeOptions = signal([
        { containerType: "smartphone", description: "", token_types: ["push"] },
        { containerType: "generic", description: "", token_types: ["push"] }
      ]);
      mockableService.compatibleWithSelectedTokenType = signal("push");
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
      TestBed.tick();
      const req = httpMock.expectOne(
        (r) => r.url === "/container/" && r.params.get("no_token") === "1" && r.params.get("type") === "smartphone,generic"
      );
      req.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
    });

    it("does not fire the request when no compatible container type exists", () => {
      mockableService.containerTypeOptions = signal([
        { containerType: "smartphone", description: "", token_types: ["push"] }
      ]);
      mockableService.compatibleWithSelectedTokenType = signal("certificate");
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("no_token") === "1");
    });

    it("includes serial filter when selectedContainerSerial is set", async () => {
      containerService.selectedContainerSerial.set("CONT1");
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
      TestBed.tick();
      const req = httpMock.expectOne((r) => r.url === "/container/" && r.params.get("container_serial") === "*CONT1*");
      req.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
    });

    describe("filterContainersByTokenOwner", () => {
      beforeEach(() => {
        jest.spyOn(tokenServiceMock.tokenDetailResource, "hasValue").mockReturnValue(true);
        jest.spyOn(tokenServiceMock.tokenDetailResource, "value").mockReturnValue({
          result: { value: { tokens: [{ container_serial: "", username: "alice", user_realm: "realm1" }] } }
        } as unknown as PiResponse<Tokens>);
        contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_DETAILS + "SERIAL1");
      });

      it("does not include user or realm when filter is off", () => {
        TestBed.tick();
        const httpRequest = httpMock.expectOne(
          (request) =>
            request.url === "/container/" &&
            request.params.get("no_token") === "1" &&
            !request.params.has("user") &&
            !request.params.has("realm")
        );
        httpRequest.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
      });

      it("includes user and realm when filter is on", () => {
        containerService.filterContainersByTokenOwner.set(true);
        TestBed.tick();
        const httpRequest = httpMock.expectOne(
          (request) =>
            request.url === "/container/" &&
            request.params.get("no_token") === "1" &&
            request.params.get("user") === "alice" &&
            request.params.get("realm") === "realm1"
        );
        httpRequest.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
      });

      it("omits user and realm when filter is on but token has no username", () => {
        jest.spyOn(tokenServiceMock.tokenDetailResource, "value").mockReturnValue({
          result: { value: { tokens: [{ container_serial: "", username: "", user_realm: "realm1" }] } }
        } as unknown as PiResponse<Tokens>);
        containerService.filterContainersByTokenOwner.set(true);
        TestBed.tick();
        const httpRequest = httpMock.expectOne(
          (request) =>
            request.url === "/container/" &&
            request.params.get("no_token") === "1" &&
            !request.params.has("user") &&
            !request.params.has("realm")
        );
        httpRequest.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
      });

      it("resets to false on route change", () => {
        containerService.filterContainersByTokenOwner.set(true);
        contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
        expect(containerService.filterContainersByTokenOwner()).toBe(false);
        httpMock
          .match((request) => request.url === "/container/")
          .forEach((pendingRequest) => pendingRequest.flush(MockPiResponse.fromValue({ containers: [], count: 0 })));
      });
    });
  });

  describe("userContainersResource", () => {
    let userServiceMock: MockUserService;

    const flushPending = () =>
      httpMock
        .match((request) => request.url === "/container/")
        .forEach((pendingRequest) => pendingRequest.flush(MockPiResponse.fromValue({ containers: [], count: 0 })));

    beforeEach(() => {
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
      userServiceMock.detailsUser.set({ username: "alice", realm: "realm1" });
      userServiceMock.selectedUserRealm.set("realm1");
    });

    it("does not load when not on user details page", () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("realm") === "realm1");
      flushPending();
    });

    it("does not load when container_list is not allowed", () => {
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
      contentServiceMock.routeUrl.set(ROUTE_PATHS.USERS_DETAILS + "/alice");
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.get("realm") === "realm1");
      flushPending();
    });

    it("loads on user details page with no_token, user, and realm params", () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.USERS_DETAILS + "/alice");
      TestBed.tick();
      const httpRequest = httpMock.expectOne(
        (request) =>
          request.url === "/container/" &&
          request.params.get("no_token") === "1" &&
          request.params.get("realm") === "realm1"
      );
      expect(httpRequest.request.method).toBe("GET");
      expect(httpRequest.request.params.get("user")).toBe("alice");
      httpRequest.flush(MockPiResponse.fromValue({ containers: [], count: 0 }));
      flushPending();
    });

    it("omits realm when selectedUserRealm is empty", () => {
      userServiceMock.selectedUserRealm.set("");
      contentServiceMock.routeUrl.set(ROUTE_PATHS.USERS_DETAILS + "/alice");
      TestBed.tick();
      httpMock.expectNone((r) => r.url === "/container/" && r.params.has("realm"));
      flushPending();
    });
  });

  describe("compareWithTemplate", () => {
    const containerWithTemplate = (serial: string, template: string | undefined): ContainerDetails => ({
      count: 1,
      containers: [{ serial, type: "", tokens: [], users: [], realms: [], states: [], template } as ContainerDetailData]
    });

    it("returns early when serial is empty", async () => {
      containerService.containerSerial.set("");
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
      await containerService.compareWithTemplate();
      expect(consoleSpy).toHaveBeenCalled();
      expect(containerService.templateComparison()).toBeNull();
      consoleSpy.mockRestore();
    });

    it("returns early when container has no template", async () => {
      containerService.containerSerial.set("CONT-1");
      containerService.containerDetails.set(containerWithTemplate("CONT-1", undefined));
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
      await containerService.compareWithTemplate();
      expect(consoleSpy).toHaveBeenCalled();
      expect(containerService.templateComparison()).toBeNull();
      consoleSpy.mockRestore();
    });

    it("fetches comparison result and sets templateComparison", async () => {
      containerService.containerSerial.set("CONT-1");
      containerService.containerDetails.set(containerWithTemplate("CONT-1", "myTemplate"));

      const comparisonResult: TemplateComparisonResult = {
        "CONT-1": { tokens: { additional: [], equal: true, missing: [] } }
      };
      jest
        .spyOn(http, "get")
        .mockReturnValue(
          of({ result: { value: comparisonResult } } as unknown as PiResponse<TemplateComparisonResult>)
        );

      await containerService.compareWithTemplate();

      expect(http.get).toHaveBeenCalledWith(
        expect.stringContaining("myTemplate/compare?container_serial=CONT-1"),
        expect.anything()
      );
      expect(containerService.templateComparison()).toEqual(comparisonResult);
    });

    it("shows snackbar on HTTP error", async () => {
      containerService.containerSerial.set("CONT-1");
      containerService.containerDetails.set(containerWithTemplate("CONT-1", "myTemplate"));

      jest
        .spyOn(http, "get")
        .mockReturnValue(throwError(() => ({ error: { result: { error: { message: "Comparison failed" } } } })));

      await containerService.compareWithTemplate();
      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to compare: Comparison failed");
      expect(containerService.templateComparison()).toBeNull();
    });
  });

  describe("setStates", () => {
    it("posts states as comma-separated string to the correct URL", async () => {
      const post = jest.spyOn(http, "post").mockReturnValue(of({}));
      await lastValueFrom(containerService.setStates("cS", ["active", "lost"]));
      expect(post).toHaveBeenCalledWith(
        `${containerService.containerBaseUrl}cS/states`,
        { states: "active,lost" },
        expect.objectContaining({ headers: expect.anything() })
      );
    });

    it("posts a single state without trailing comma", async () => {
      const post = jest.spyOn(http, "post").mockReturnValue(of({}));
      await lastValueFrom(containerService.setStates("cS", ["disabled"]));
      expect(post).toHaveBeenCalledWith(
        `${containerService.containerBaseUrl}cS/states`,
        { states: "disabled" },
        expect.objectContaining({ headers: expect.anything() })
      );
    });

    it("error path shows snackbar and rethrows", async () => {
      jest.spyOn(http, "post").mockReturnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
      await expect(lastValueFrom(containerService.setStates("cS", ["active"]))).rejects.toBeDefined();
      expect(notificationServiceMock.error).toHaveBeenCalledWith(
        expect.stringContaining("Failed to set container states.")
      );
    });

    it("rejects with an error and notifies when states array is empty", async () => {
      const post = jest.spyOn(http, "post");
      await expect(lastValueFrom(containerService.setStates("cS", []))).rejects.toThrow(
        "setStates called with empty states array"
      );
      expect(notificationServiceMock.error).toHaveBeenCalledWith(
        "Cannot save container states: at least one state must be selected."
      );
      expect(post).not.toHaveBeenCalled();
    });
  });

  describe("templateComparison", () => {
    it("resets to null when containerSerial changes", () => {
      containerService.containerSerial.set("CONT-A");
      containerService.templateComparison.set({ "CONT-A": { tokens: { additional: [], equal: true, missing: [] } } });
      expect(containerService.templateComparison()).not.toBeNull();

      containerService.containerSerial.set("CONT-B");
      expect(containerService.templateComparison()).toBeNull();
    });

    it("retains value while containerSerial is unchanged", () => {
      containerService.containerSerial.set("CONT-A");
      const result: TemplateComparisonResult = {
        "CONT-A": { tokens: { additional: ["tok1"], equal: false, missing: [] } }
      };
      containerService.templateComparison.set(result);

      containerService.containerSerial.set("CONT-A");
      expect(containerService.templateComparison()).toEqual(result);
    });
  });
});

describe("toWildcardParam", () => {
  const plain = new Set(["user", "type"]);

  it("returns empty object for null value", () => {
    expect(toWildcardParam("container_serial", null, plain)).toEqual({});
  });

  it("returns empty object for undefined value", () => {
    expect(toWildcardParam("container_serial", undefined, plain)).toEqual({});
  });

  it("returns empty object for empty string", () => {
    expect(toWildcardParam("container_serial", "", plain)).toEqual({});
  });

  it("returns empty object for whitespace-only string", () => {
    expect(toWildcardParam("container_serial", "   ", plain)).toEqual({});
  });

  it("returns empty object for single wildcard (invalid filter value)", () => {
    expect(toWildcardParam("container_serial", "*", plain)).toEqual({});
  });

  it("wraps non-plain key with wildcards", () => {
    expect(toWildcardParam("container_serial", "CONT1", plain)).toEqual({ container_serial: "*CONT1*" });
  });

  it("does not wrap plain key with wildcards", () => {
    expect(toWildcardParam("type", "hotp", plain)).toEqual({ type: "hotp" });
    expect(toWildcardParam("user", "alice", plain)).toEqual({ user: "alice" });
  });

  it("trims whitespace before wrapping", () => {
    expect(toWildcardParam("container_serial", "  CONT1  ", plain)).toEqual({ container_serial: "*CONT1*" });
  });

  it("trims whitespace for plain keys too", () => {
    expect(toWildcardParam("type", "  hotp  ", plain)).toEqual({ type: "hotp" });
  });

  it("works with an empty plain keys set (always wraps)", () => {
    expect(toWildcardParam("type", "hotp", new Set())).toEqual({ type: "*hotp*" });
  });
});
