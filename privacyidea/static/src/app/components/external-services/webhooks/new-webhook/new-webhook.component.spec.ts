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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { Webhook, WEBHOOK_CENSORED, WebhookService } from "@services/webhook/webhook.service";
import { MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockWebhookService } from "@testing/mock-services/mock-webhook-service";
import { of } from "rxjs";
import { NewWebhookComponent } from "./new-webhook.component";

const STORED_WEBHOOK: Webhook = {
  identifier: "siem",
  description: "Security monitoring",
  url: "https://siem.example.com/hook",
  http_method: "POST",
  content_type: "application/json",
  default_payload: "{\"source\": \"privacyidea\"}",
  auth_type: "header",
  verify_tls: true,
  timeout: 5,
  headers: { "X-Api-Key": WEBHOOK_CENSORED, "X-Source": "privacyidea" },
  secret_headers: ["X-Api-Key"]
};

describe("NewWebhookComponent", () => {
  let component: NewWebhookComponent;
  let fixture: ComponentFixture<NewWebhookComponent>;
  let webhookServiceMock: MockWebhookService;
  let router: Router;

  async function setUp(identifier?: string): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [NewWebhookComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap(identifier ? { identifier } : {})) }
        },
        { provide: WebhookService, useClass: MockWebhookService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    webhookServiceMock = TestBed.inject(WebhookService) as unknown as MockWebhookService;
    webhookServiceMock.webhooks.set([STORED_WEBHOOK]);
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    fixture = TestBed.createComponent(NewWebhookComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  afterEach(() => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();
  });

  describe("create mode", () => {
    beforeEach(async () => {
      await setUp();
    });

    it("should create", () => {
      expect(component).toBeTruthy();
      expect(component.isEditMode()).toBe(false);
    });

    it("starts from the server's own defaults", () => {
      const model = component.webhookModel();
      expect(model.identifier).toBe("");
      expect(model.http_method).toBe("POST");
      expect(model.content_type).toBe("application/json");
      expect(model.auth_type).toBe("none");
      // Verification is on unless an admin deliberately turns it off.
      expect(model.verify_tls).toBe(true);
      expect(model.timeout).toBe(3);
    });

    it("requires an identifier and an http(s) URL", () => {
      component.webhookModel.update((m) => ({ ...m, identifier: "siem", url: "ftp://example.com" }));
      expect(component.canSave).toBe(false);
      component.webhookModel.update((m) => ({ ...m, url: "https://example.com/hook" }));
      expect(component.canSave).toBe(true);
    });

    it("rejects a timeout that is not positive", () => {
      component.webhookModel.update((m) => ({
        ...m,
        identifier: "siem",
        url: "https://example.com/hook",
        timeout: 0
      }));
      expect(component.canSave).toBe(false);
    });

    it("insists on a username for basic authentication only", () => {
      component.webhookModel.update((m) => ({
        ...m,
        identifier: "siem",
        url: "https://example.com/hook",
        auth_type: "basic"
      }));
      expect(component.canSave).toBe(false);
      component.webhookModel.update((m) => ({ ...m, username: "pi" }));
      expect(component.canSave).toBe(true);
    });

    it("cannot test an unsaved webhook", () => {
      // The endpoint fires the stored definition, so testing here would report on something else.
      expect(component.canTest()).toBe(false);
    });

    it("saves the header table as a record plus the secret flags", async () => {
      component.webhookModel.update((m) => ({ ...m, identifier: "siem", url: "https://example.com/hook" }));
      component.addHeader();
      component.updateHeader(0, { key: "X-Api-Key", value: "s3cr3t", secret: true });
      component.addHeader();
      component.updateHeader(1, { key: "X-Source", value: "privacyidea" });
      // An unfinished row carries no name and is not a header to send.
      component.addHeader();

      await component.save();

      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: { "X-Api-Key": "s3cr3t", "X-Source": "privacyidea" },
          secret_headers: ["X-Api-Key"]
        })
      );
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
    });

    it("does not save an invalid form", async () => {
      expect(await component.save()).toBe(false);
      expect(webhookServiceMock.postWebhook).not.toHaveBeenCalled();
    });
  });

  describe("edit mode", () => {
    beforeEach(async () => {
      await setUp("siem");
    });

    it("loads the stored definition, headers included", () => {
      expect(component.isEditMode()).toBe(true);
      const model = component.webhookModel();
      expect(model.identifier).toBe("siem");
      expect(model.url).toBe("https://siem.example.com/hook");
      expect(model.timeout).toBe(5);
      expect(component.headers()).toEqual([
        { key: "X-Api-Key", value: WEBHOOK_CENSORED, secret: true },
        { key: "X-Source", value: "privacyidea", secret: false }
      ]);
    });

    it("sends the censored placeholder back unchanged, keeping the stored secret", async () => {
      await component.save();
      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(
        expect.objectContaining({ headers: expect.objectContaining({ "X-Api-Key": WEBHOOK_CENSORED }) })
      );
    });

    it("can test an unchanged definition, but not once it is edited", () => {
      expect(component.canTest()).toBe(true);
      component.updateHeader(0, { value: "new" });
      expect(component.canTest()).toBe(false);
    });

    it("counts a header-only edit as an unsaved change", () => {
      expect(component.hasChanges).toBe(false);
      component.removeHeader(0);
      expect(component.hasChanges).toBe(true);
    });

    it("fires the stored webhook and keeps what the endpoint answered", async () => {
      await component.test();
      expect(webhookServiceMock.testWebhook).toHaveBeenCalledWith("siem");
      expect(component.testResult()?.success).toBe(true);
    });
  });
});
