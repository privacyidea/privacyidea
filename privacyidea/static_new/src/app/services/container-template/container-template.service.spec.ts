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

import { TestBed } from "@angular/core/testing";
import { ContainerTemplateService } from "./container-template.service";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ContainerService, ContainerTemplate } from "../container/container.service";
import { ContentService } from "../content/content.service";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { ROUTE_PATHS } from "../../route_paths";
import { environment } from "../../../environments/environment";
import { provideHttpClient } from "@angular/common/http";
import {
  MockContainerService,
  MockContentService,
  MockNotificationService,
  MockPiResponse
} from "../../../testing/mock-services";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";

describe("ContainerTemplateService", () => {
  let service: ContainerTemplateService;
  let httpMock: HttpTestingController;
  let authServiceMock: MockAuthService;
  let contentServiceMock: MockContentService;
  let containerServiceMock: MockContainerService;
  let notificationServiceMock: MockNotificationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ContainerTemplateService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });
    service = TestBed.inject(ContainerTemplateService);
    httpMock = TestBed.inject(HttpTestingController);
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    authServiceMock.actionAllowed.mockReturnValue(true);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("templatesResource", () => {
    beforeEach(() => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
    });

    afterEach(() => {
      const req = httpMock.match(`${environment.proxyUrl}/container/template/tokentypes`);
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should fetch templates when on the correct route and with permission", async () => {
      TestBed.tick();

      const req = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      req.flush({ result: { value: { templates: [{ name: "template1" }] } } });
      TestBed.tick();
      await Promise.resolve();

      const value = service.templatesResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value?.templates).toBeDefined();
      expect(value?.result?.value?.templates).toEqual([{ name: "template1" }]);
      expect(service.templates()).toEqual([{ name: "template1" }]);
    });

    it("should not fetch templates if action is not allowed", async () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.tick();

      httpMock.expectNone(`${service.containerTemplateBaseUrl}?container_type=test-type`);
      const value = service.templatesResource.value();
      expect(value).toBeUndefined();
      expect(service.templates()).toEqual([]);
    });

    it("should not fetch templates if not on the correct route", async () => {
      contentServiceMock.routeUrl.set("/wrong/route");
      TestBed.tick();
      await Promise.resolve();

      httpMock.expectNone(`${service.containerTemplateBaseUrl}?container_type=test-type`);
      const value = service.templatesResource.value();
      expect(value).toBeUndefined();
      expect(service.templates()).toEqual([]);
    });

    it("should handle http error", async () => {
      TestBed.tick();

      const req = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.templates()).toEqual([]);
    });
  });

  describe("templateTokentypesResource", () => {
    beforeEach(() => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
    });

    afterEach(() => {
      const req = httpMock.match(`${service.containerTemplateBaseUrl}`);
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should fetch token types", async () => {
      TestBed.tick();

      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = { type1: { description: "Type 1", token_types: ["token1"] } };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });
      TestBed.tick();
      await Promise.resolve();

      const value = service.templateTokenTypesResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(mockTokenTypes);
      expect(service.templateTokenTypes()).toEqual(mockTokenTypes);
    });

    it("should handle http error", async () => {
      TestBed.tick();

      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      tokenTypesReq.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      TestBed.tick();
      await Promise.resolve();

      expect(service.templateTokenTypes()).toEqual({});
    });

    it("should not fetch token types if not on the correct route", async () => {
      contentServiceMock.routeUrl.set("/wrong/route");
      TestBed.tick();

      httpMock.expectNone(`${environment.proxyUrl}/container/template/tokentypes`);
      const value = service.templateTokenTypesResource.value();
      expect(value).toBeUndefined();
      expect(service.templateTokenTypes()).toEqual({});
    });

    it("should not fetch token types if action is not allowed", async () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.tick();

      httpMock.expectNone(`${environment.proxyUrl}/container/template/tokentypes`);
      const value = service.templateTokenTypesResource.value();
      expect(value).toBeUndefined();
      expect(service.templateTokenTypes()).toEqual({});
    });
  });

  describe("getTokenTypesForContainerType", () => {
    beforeEach(() => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
    });

    afterEach(() => {
      const req = [
        ...httpMock.match(`${environment.proxyUrl}/container/template/tokentypes`),
        ...httpMock.match(`${service.containerTemplateBaseUrl}`)
      ];
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should return token types for a given container type", async () => {
      TestBed.tick();

      const templatesReq = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      templatesReq.flush({ result: { value: { templates: [] } } });
      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = { type1: { description: "Type 1", token_types: ["token1", "token2"] } };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });

      TestBed.tick();
      await Promise.resolve();

      expect(service.getTokenTypesForContainerType("type1")).toEqual(["token1", "token2"]);
    });

    it("should return an empty array for a non-existent container type", async () => {
      TestBed.tick();

      const templatesReq = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      templatesReq.flush({ result: { value: { templates: [] } } });
      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = { type1: { description: "Type 1", token_types: ["token1", "token2"] } };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });

      TestBed.tick();
      await Promise.resolve();

      expect(service.getTokenTypesForContainerType("non-existent")).toEqual([]);
    });
  });

  describe("deleteTemplate", () => {
    it("should send DELETE request, reload and show snackbar", async () => {
      const spy = jest.spyOn(service.templatesResource, "reload");
      const deletePromise = service.deleteTemplate("test-1");

      const req = httpMock.expectOne((req) => req.url.includes("/container/template/test-1"));
      req.flush({});
      await deletePromise;

      expect(spy).toHaveBeenCalled();
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Successfully deleted template.");
    });

    it("should throw error on delete", async () => {
      const templateName = "template-to-fail";
      const deletePromise = service.deleteTemplate(templateName).catch(() => {
      });
      const req = httpMock.expectOne((req) => req.url.includes(`/container/template/${templateName}`));

      req.flush("Error", { status: 500, statusText: "Server Error" });

      await deletePromise;
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining("Failed to delete template")
      );
    });

    it("should check permissions and throw if denied", async () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.tick();

      const templateName = "template-to-delete";

      await expect(service.deleteTemplate(templateName)).rejects.toThrow("Permission denied");

      httpMock.expectNone(`/container/template/${templateName}`);
      expect(authServiceMock.actionAllowed).toHaveBeenCalledWith("container_template_delete");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "You are not allowed to delete container templates."
      );
    });
  });

  describe("deleteTemplates", () => {
    it("should delete multiple templates sequentially, reload once and show success notification", async () => {
      const spy = jest.spyOn(service.templatesResource, "reload");
      const templateNames = ["template-1", "template-2"];

      const deletePromise = service.deleteTemplates(templateNames);

      const req1 = httpMock.expectOne((req) => req.url.includes(`/container/template/${templateNames[0]}`));
      req1.flush({});

      await Promise.resolve();
      await Promise.resolve();

      const req2 = httpMock.expectOne((req) => req.url.includes(`/container/template/${templateNames[1]}`));
      req2.flush({});

      await deletePromise;

      expect(spy).toHaveBeenCalledTimes(1);
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Successfully deleted templates.");
    });

    it("should stop execution if one deletion fails and show error notification", async () => {
      const spy = jest.spyOn(service.templatesResource, "reload");
      const templateNames = ["template-1", "template-2"];

      const deletePromise = service.deleteTemplates(templateNames).catch(() => {
      });

      const req1 = httpMock.expectOne((req) => req.url.includes(`/container/template/${templateNames[0]}`));
      req1.flush(
        { result: { error: { message: "Internal Server Error" } } },
        { status: 500, statusText: "Server Error" }
      );

      await deletePromise;

      httpMock.expectNone((req) => req.url.includes(`/container/template/${templateNames[1]}`));

      expect(spy).not.toHaveBeenCalled();
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining("Failed to delete templates. Internal Server Error")
      );
    });
  });

  describe("postTemplateEdits", () => {
    const template: ContainerTemplate = {
      name: "test-template",
      container_type: "generic",
      default: false,
      template_options: {
        tokens: []
      }
    };

    beforeEach(() => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
      TestBed.tick();
      const reqs = httpMock.match(() => true);
      reqs.forEach((req) => req.flush({ result: { value: {} } }));
    });

    it("should send a POST request, reload and show success notification", async () => {
      const spy = jest.spyOn(service.templatesResource, "reload");
      const promise = service.postTemplateEdits(template);

      const req = httpMock.expectOne(
        `${environment.proxyUrl}/container/${template.container_type}/template/${template.name}`
      );
      expect(req.request.method).toBe("POST");
      req.flush({});

      await promise;

      expect(spy).toHaveBeenCalled();
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(`Successfully saved template edits.`);
    });

    it("should handle error on post and show error notification", async () => {
      const promise = service.postTemplateEdits(template);

      const req = httpMock.expectOne(
        `${environment.proxyUrl}/container/${template.container_type}/template/${template.name}`
      );
      req.flush({ result: { error: { message: "Error message" } } }, { status: 500, statusText: "Server Error" });

      await promise;

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to save template edits. Error message");
    });
  });

  describe("canSaveTemplate", () => {
    let validTemplate: ContainerTemplate;
    beforeEach(() => {
      validTemplate = {
        name: "valid-template",
        container_type: "generic",
        default: false,
        template_options: {
          tokens: [{ type: "hotp", genkey: false, hashlib: "", otplen: 6, timeStep: 0, user: false }]
        }
      };
    });
    it("should return true on valid template", () => {
      expect(service.canSaveTemplate(validTemplate)).toBe(true);
    });
    it("should return false on empty name", () => {
      const invalidTemplate = { ...validTemplate, name: "   " };
      expect(service.canSaveTemplate(invalidTemplate)).toBe(false);
    });
    it("should return false on empty token list", () => {
      const invalidTemplate = {
        ...validTemplate,
        template_options: { ...validTemplate.template_options, tokens: [] }
      };
      expect(service.canSaveTemplate(invalidTemplate)).toBe(false);
    });
  });

  describe("Error handling", () => {
    afterEach(() => {
      const req = [
        ...httpMock.match(`${environment.proxyUrl}/container/template/tokentypes`),
        ...httpMock.match(`${service.containerTemplateBaseUrl}`)
      ];
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should show a generic error notification on delete if error response contains no message", async () => {
      const deletePromise = service.deleteTemplate("some-template").catch(() => {
      });

      const req = httpMock.expectOne((req) => req.url.includes(`/container/template/some-template`));
      req.flush({ result: { error: {} } }, { status: 500, statusText: "Internal Server Error" });

      await deletePromise;

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to delete template. ");
    });

    it("should show a generic error notification on post if error response contains no message", async () => {
      const template: ContainerTemplate = {
        name: "test-template",
        container_type: "generic",
        default: false,
        template_options: {
          tokens: []
        }
      };
      const promise = service.postTemplateEdits(template);
      const req = httpMock.expectOne(`/container/generic/template/test-template`);
      req.flush({ result: { error: {} } }, { status: 500, statusText: "Internal Server Error" });

      await promise;
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to save template edits. ");
    });
  });
});
