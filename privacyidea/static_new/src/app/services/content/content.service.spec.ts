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
import { TestBed } from "@angular/core/testing";
import { NavigationEnd, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { Subject } from "rxjs";
import { ContentService } from "./content.service";

describe("ContentService", () => {
  let service: ContentService;

  let events$: Subject<NavigationEnd>;
  let mockRouter: {
    url: string;
    events: Subject<NavigationEnd>;
    navigateByUrl: jest.Mock<Promise<boolean>, [string]>;
  };

  const emitNav = (url: string) => {
    mockRouter.url = url;
    events$.next(new NavigationEnd(Date.now(), url, url));
  };

  beforeEach(() => {
    events$ = new Subject<NavigationEnd>();
    mockRouter = {
      url: "/start",
      events: events$,
      navigateByUrl: jest.fn(async (url: string) => {
        emitNav(url);
        return true;
      })
    };

    TestBed.configureTestingModule({
      providers: [provideHttpClient(), ContentService, { provide: Router, useValue: mockRouter }]
    });

    service = TestBed.inject(ContentService);
  });

  it("creates the service", () => {
    expect(service).toBeTruthy();
  });

  it("initial routeUrl/previousUrl mirror the starting router.url", () => {
    expect(service.routeUrl()).toBe("/start");
    expect(service.previousUrl()).toBe("/start");
  });

  it("updates routeUrl and previousUrl on NavigationEnd events", () => {
    emitNav("/first");
    expect(service.previousUrl()).toBe("/start");
    expect(service.routeUrl()).toBe("/first");

    emitNav("/second");
    expect(service.previousUrl()).toBe("/first");
    expect(service.routeUrl()).toBe("/second");
  });

  it("parses queryParams from the current route", () => {
    expect(service.queryParams()).toEqual({});

    emitNav(ROUTE_PATHS.TOKENS_ENROLLMENT + "?realm=defrealm&user=root");
    expect(service.queryParams()).toEqual({ realm: "defrealm", user: "root" });

    emitNav(ROUTE_PATHS.TOKENS_ENROLLMENT);
    expect(service.queryParams()).toEqual({});
  });

  it("route checks match the base path even with query parameters", () => {
    emitNav(ROUTE_PATHS.TOKENS_ENROLLMENT + "?realm=defrealm&user=root");
    expect(service.onTokensEnrollment()).toBe(true);
    expect(service.onTokens()).toBe(false);

    emitNav(ROUTE_PATHS.CONTAINERS_CREATE + "?user=root");
    expect(service.onContainersCreate()).toBe(true);
  });

  describe("route flags", () => {
    // Every flag with the URLs it has to recognize. Each URL is checked twice: bare, and with query
    // parameters appended, because navigation now carries the realm/user selection in the query string.
    const routeFlagCases: ReadonlyArray<{
      name: string;
      read: (service: ContentService) => boolean;
      urls: string[];
    }> = [
      { name: "onLogin", read: (s) => s.onLogin(), urls: [ROUTE_PATHS.LOGIN] },
      { name: "onAudit", read: (s) => s.onAudit(), urls: [ROUTE_PATHS.AUDIT] },
      { name: "onClients", read: (s) => s.onClients(), urls: [ROUTE_PATHS.CLIENTS] },
      { name: "onTokens", read: (s) => s.onTokens(), urls: [ROUTE_PATHS.TOKENS] },
      { name: "onUsers", read: (s) => s.onUsers(), urls: [ROUTE_PATHS.USERS] },
      {
        name: "onPolicies",
        read: (s) => s.onPolicies(),
        urls: [ROUTE_PATHS.POLICIES, ROUTE_PATHS.POLICIES_NEW, ROUTE_PATHS.POLICIES_DETAILS + "pol1"]
      },
      { name: "onTokenDetails", read: (s) => s.onTokenDetails(), urls: [ROUTE_PATHS.TOKENS_DETAILS + "SER1"] },
      { name: "onUserDetails", read: (s) => s.onUserDetails(), urls: [ROUTE_PATHS.USERS_DETAILS + "/alice"] },
      {
        name: "onUserDetailsSelfService",
        read: (s) => s.onUserDetailsSelfService(),
        urls: [ROUTE_PATHS.USERS_DETAILS]
      },
      { name: "onUserRealms", read: (s) => s.onUserRealms(), urls: [ROUTE_PATHS.USERS_REALMS] },
      { name: "onUsersResolvers", read: (s) => s.onUsersResolvers(), urls: [ROUTE_PATHS.USERS_RESOLVERS] },
      { name: "onTokensEnrollment", read: (s) => s.onTokensEnrollment(), urls: [ROUTE_PATHS.TOKENS_ENROLLMENT] },
      { name: "onTokensChallenges", read: (s) => s.onTokensChallenges(), urls: [ROUTE_PATHS.TOKENS_CHALLENGES] },
      { name: "onTokensApplications", read: (s) => s.onTokensApplications(), urls: [ROUTE_PATHS.TOKENS_APPLICATIONS] },
      { name: "onTokensGetSerial", read: (s) => s.onTokensGetSerial(), urls: [ROUTE_PATHS.TOKENS_GET_SERIAL] },
      { name: "onTokensImport", read: (s) => s.onTokensImport(), urls: [ROUTE_PATHS.TOKENS_IMPORT] },
      { name: "onTokensAssignToken", read: (s) => s.onTokensAssignToken(), urls: [ROUTE_PATHS.TOKENS_ASSIGN_TOKEN] },
      { name: "onTokensWizard", read: (s) => s.onTokensWizard(), urls: [ROUTE_PATHS.TOKENS_WIZARD] },
      {
        name: "onAnyTokensRoute",
        read: (s) => s.onAnyTokensRoute(),
        urls: [ROUTE_PATHS.TOKENS, ROUTE_PATHS.TOKENS_ENROLLMENT]
      },
      {
        name: "onAnyUsersRoute",
        read: (s) => s.onAnyUsersRoute(),
        urls: [ROUTE_PATHS.USERS, ROUTE_PATHS.USERS_REALMS]
      },
      { name: "onContainers", read: (s) => s.onContainers(), urls: [ROUTE_PATHS.CONTAINERS] },
      {
        name: "onContainersCreate",
        read: (s) => s.onContainersCreate(),
        urls: [ROUTE_PATHS.CONTAINERS_CREATE, ROUTE_PATHS.CONTAINERS_WIZARD]
      },
      { name: "onContainersWizard", read: (s) => s.onContainersWizard(), urls: [ROUTE_PATHS.CONTAINERS_WIZARD] },
      {
        name: "onContainersDetails",
        read: (s) => s.onContainersDetails(),
        urls: [ROUTE_PATHS.CONTAINERS_DETAILS + "CONT1"]
      },
      {
        name: "onAnyContainerTemplatesRoute",
        read: (s) => s.onAnyContainerTemplatesRoute(),
        urls: [
          ROUTE_PATHS.CONTAINERS_TEMPLATES,
          ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE,
          ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS + "myTemplate"
        ]
      },
      {
        name: "onEvents",
        read: (s) => s.onEvents(),
        urls: [ROUTE_PATHS.EVENTS, ROUTE_PATHS.EVENTS_NEW, ROUTE_PATHS.EVENTS_DETAILS + "1"]
      },
      {
        name: "onConfigurationSystem",
        read: (s) => s.onConfigurationSystem(),
        urls: [ROUTE_PATHS.CONFIGURATION_SYSTEM]
      },
      {
        name: "onConfigurationTokenTypes",
        read: (s) => s.onConfigurationTokenTypes(),
        urls: [ROUTE_PATHS.CONFIGURATION_TOKENTYPES]
      },
      {
        name: "onConfigurationMachines",
        read: (s) => s.onConfigurationMachines(),
        urls: [ROUTE_PATHS.CONFIGURATION_MACHINES, ROUTE_PATHS.CONFIGURATION_MACHINES_DETAILS + "host1"]
      },
      {
        name: "onConfigurationPeriodicTasks",
        read: (s) => s.onConfigurationPeriodicTasks(),
        urls: [
          ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS,
          ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS_NEW,
          ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS_DETAILS + "1"
        ]
      },
      { name: "onSubscription", read: (s) => s.onSubscription(), urls: [ROUTE_PATHS.SUBSCRIPTION] },
      {
        name: "onMachineResolver",
        read: (s) => s.onMachineResolver(),
        urls: [
          ROUTE_PATHS.MACHINE_RESOLVER,
          ROUTE_PATHS.MACHINE_RESOLVER_NEW,
          ROUTE_PATHS.MACHINE_RESOLVER_DETAILS + "hosts1"
        ]
      },
      {
        name: "onExternalSmtp",
        read: (s) => s.onExternalSmtp(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_SMTP,
          ROUTE_PATHS.EXTERNAL_SERVICES_SMTP_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_SMTP_DETAILS + "mailer"
        ]
      },
      {
        name: "onExternalRadius",
        read: (s) => s.onExternalRadius(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS,
          ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS_DETAILS + "radius1"
        ]
      },
      {
        name: "onExternalSms",
        read: (s) => s.onExternalSms(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_SMS,
          ROUTE_PATHS.EXTERNAL_SERVICES_SMS_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_SMS_DETAILS + "gateway1"
        ]
      },
      {
        name: "onExternalCaConnectors",
        read: (s) => s.onExternalCaConnectors(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS,
          ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_DETAILS + "ca1"
        ]
      },
      {
        name: "onExternalPrivacyIdea",
        read: (s) => s.onExternalPrivacyIdea(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA,
          ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA_DETAILS + "pi1"
        ]
      },
      {
        name: "onExternalTokenGroups",
        read: (s) => s.onExternalTokenGroups(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS,
          ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS_DETAILS + "group1"
        ]
      },
      {
        name: "onExternalServiceIds",
        read: (s) => s.onExternalServiceIds(),
        urls: [
          ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS,
          ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS_NEW,
          ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS_DETAILS + "service1"
        ]
      }
    ];

    it.each(routeFlagCases)("$name matches its routes with and without query parameters", ({ read, urls }) => {
      emitNav("/somewhere-else");
      expect(read(service)).toBe(false);

      for (const url of urls) {
        emitNav(url);
        expect(read(service)).toBe(true);

        emitNav(url + "?realm=defrealm&user=root");
        expect(read(service)).toBe(true);
      }
    });
  });

  it("onTokenEnrollmentLikely is true for enrollment related routes", () => {
    expect(service.onTokenEnrollmentLikely()).toBe(false);

    emitNav(ROUTE_PATHS.TOKENS_ENROLLMENT);
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.TOKENS_WIZARD);
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.TOKENS_DETAILS + "/SER1");
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
    expect(service.onTokenEnrollmentLikely()).toBe(true);

    emitNav(ROUTE_PATHS.TOKENS);
    expect(service.onTokenEnrollmentLikely()).toBe(false);
  });

  describe("container route signals", () => {
    it("onContainersCreate is true for CONTAINERS_CREATE and CONTAINERS_WIZARD paths", () => {
      expect(service.onContainersCreate()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_CREATE);
      expect(service.onContainersCreate()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_WIZARD);
      expect(service.onContainersCreate()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS);
      expect(service.onContainersCreate()).toBe(false);
    });
  });

  describe("template route signals", () => {
    it("onContainersTemplates is true only for exact CONTAINERS_TEMPLATES path", () => {
      expect(service.onContainersTemplates()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
      expect(service.onContainersTemplates()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES + "/something");
      expect(service.onContainersTemplates()).toBe(false);
    });

    it("onContainersTemplatesCreate is true only for exact CONTAINERS_TEMPLATES_CREATE path", () => {
      expect(service.onContainersTemplatesCreate()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE);
      expect(service.onContainersTemplatesCreate()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
      expect(service.onContainersTemplatesCreate()).toBe(false);
    });

    it("onContainersTemplatesDetails is true for paths starting with CONTAINERS_TEMPLATES_DETAILS", () => {
      expect(service.onContainersTemplatesDetails()).toBe(false);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS + "myTemplate");
      expect(service.onContainersTemplatesDetails()).toBe(true);
      emitNav(ROUTE_PATHS.CONTAINERS_TEMPLATES);
      expect(service.onContainersTemplatesDetails()).toBe(false);
    });
  });

  describe("tokenSelected()", () => {
    it("navigates to token details and sets serial", async () => {
      emitNav("/containers");
      service.tokenSelected("SER1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_DETAILS + "SER1");
      expect(service.tokenSerial()).toBe("SER1");
      expect(service.routeUrl()).toBe(ROUTE_PATHS.TOKENS_DETAILS + "SER1");
      expect(service.previousUrl()).toBe("/containers");
    });
  });

  describe("userSelected()", () => {
    it("navigates to user details and stores username and realm", () => {
      emitNav("/tokens");
      service.userSelected("alice", "themis");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_DETAILS + "/alice?realm=themis");
      expect(service.detailsUser().username).toBe("alice");
      expect(service.detailsUser().realm).toBe("themis");
    });

    it("stores an empty realm when none is provided", () => {
      emitNav("/tokens");
      service.userSelected("alice", undefined as unknown as string);

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_DETAILS + "/alice?realm=");
      expect(service.detailsUser().realm).toBe("");
    });
  });

  describe("containerSelected()", () => {
    it("navigates to container details and sets serial", async () => {
      emitNav("/tokens");
      service.navigateContainerDetails("C1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_DETAILS + "C1");
      expect(service.containerSerial()).toBe("C1");
      expect(service.routeUrl()).toBe(ROUTE_PATHS.CONTAINERS_DETAILS + "C1");
      expect(service.previousUrl()).toBe("/tokens");
    });
  });

  describe("machineResolverSelected()", () => {
    it("navigates to machine resolver details", () => {
      emitNav("/tokens");
      service.machineResolverSelected("hosts 1");

      expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER_DETAILS + "hosts%201");
    });
  });
});
