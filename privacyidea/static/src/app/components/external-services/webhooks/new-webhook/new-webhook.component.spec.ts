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
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { Webhook, WEBHOOK_CENSORED, WebhookService } from "@services/webhook/webhook.service";
import { MockDialogService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockWebhookService } from "@testing/mock-services/mock-webhook-service";
import { of } from "rxjs";
import { NewWebhookComponent } from "./new-webhook.component";

/** POST /webhook/<identifier> and its test call require webhook_write; the list needs webhook_read. */
const WRITE_RIGHTS = ["webhook_read", "webhook_write"];

const STORED_WEBHOOK: Webhook = {
  identifier: "siem",
  description: "Security monitoring",
  url: "https://siem.example.com/hook",
  http_method: "POST",
  content_type: "application/json",
  default_payload: '{"source": "privacyidea"}',
  auth_type: "header",
  verify_tls: true,
  timeout: 5,
  urlencode_values: true,
  headers: { "X-Api-Key": WEBHOOK_CENSORED, "X-Source": "privacyidea" },
  secret_headers: ["X-Api-Key"]
};

describe("NewWebhookComponent", () => {
  let component: NewWebhookComponent;
  let fixture: ComponentFixture<NewWebhookComponent>;
  let webhookServiceMock: MockWebhookService;
  let router: Router;

  async function setUp(identifier?: string, rights: string[] = WRITE_RIGHTS): Promise<void> {
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
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });

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

  const flush = async (): Promise<void> => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };

  const formFieldOf = (label: string): HTMLElement => {
    const fields = Array.from(fixture.nativeElement.querySelectorAll("mat-form-field") as NodeListOf<HTMLElement>);
    return fields.find((field) => field.querySelector("mat-label")?.textContent?.trim() === label)!;
  };

  const clearButtonOf = (label: string): HTMLButtonElement =>
    formFieldOf(label).querySelector("app-clearable-input button") as HTMLButtonElement;

  const errorKinds = (field: { errors(): { kind: string }[] }): string[] => field.errors().map((error) => error.kind);

  /** Fills the two fields a new webhook cannot do without, so that only the rule under test decides. */
  const fillRequired = (): void => {
    component.webhookModel.update((m) => ({ ...m, identifier: "siem", url: "https://example.com/hook" }));
  };

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

    it.each([".", ".."])("rejects the reserved identifier %p", (identifier) => {
      // A browser removes these dot segments while resolving the save URL, so the POST would
      // never reach /webhook/<identifier> and the webhook would silently not be created.
      component.webhookModel.update((m) => ({ ...m, identifier, url: "https://example.com/hook" }));
      expect(
        component.webhookForm
          .identifier()
          .errors()
          .some((e) => e.kind === "reservedName")
      ).toBe(true);
      expect(component.webhookForm().valid()).toBe(false);
      expect(component.canSave).toBe(false);
    });

    it.each([
      [0, "below the minimum"],
      [3601, "above the maximum"],
      [2.5, "a fraction"]
    ])("rejects the timeout %p, %s", (timeout) => {
      // The server accepts a whole number of seconds from 1 to 3600 only.
      fillRequired();
      component.webhookModel.update((m) => ({ ...m, timeout }));
      expect(component.timeoutOutOfRange()).toBe(true);
      expect(component.canSave).toBe(false);
    });

    it.each([1, 3600])("accepts the timeout %p", (timeout) => {
      fillRequired();
      component.webhookModel.update((m) => ({ ...m, timeout }));
      expect(component.timeoutOutOfRange()).toBe(false);
      expect(component.canSave).toBe(true);
    });

    it("requires a timeout", () => {
      fillRequired();
      component.webhookModel.update((m) => ({ ...m, timeout: null }));
      expect(errorKinds(component.webhookForm.timeout())).toContain("required");
      expect(component.canSave).toBe(false);
    });

    it("refuses mTLS without a client certificate", () => {
      fillRequired();
      component.webhookModel.update((m) => ({ ...m, auth_type: "mtls" }));
      expect(errorKinds(component.webhookForm.client_certificate())).toContain("required");
      expect(component.canSave).toBe(false);

      component.webhookModel.update((m) => ({ ...m, client_certificate: "/etc/privacyidea/client.pem" }));
      expect(component.canSave).toBe(true);
    });

    it("refuses header authentication without a header", async () => {
      fillRequired();
      component.webhookModel.update((m) => ({ ...m, auth_type: "header" }));
      await flush();
      expect(errorKinds(component.webhookForm.auth_type())).toContain("headerAuthNeedsHeader");
      expect(component.canSave).toBe(false);
      // The message shows without a touch: the field the admin has to change is another one.
      expect(fixture.nativeElement.textContent).toContain("Header authentication needs at least one header.");

      component.addHeader();
      component.updateHeader(0, { key: "Authorization", value: "Bearer token", secret: true });
      await flush();
      expect(component.canSave).toBe(true);
      expect(fixture.nativeElement.textContent).not.toContain("Header authentication needs at least one header.");
    });

    it("does not count an unfinished header row for header authentication", () => {
      fillRequired();
      component.webhookModel.update((m) => ({ ...m, auth_type: "header" }));
      component.addHeader();
      expect(component.canSave).toBe(false);
    });

    describe("header names", () => {
      beforeEach(() => {
        fillRequired();
      });

      it("refuses two headers whose names differ only in case", () => {
        // HTTP header names are not case-sensitive, so the server would send only one of them.
        component.addHeader();
        component.updateHeader(0, { key: "X-Api-Key", value: "first" });
        component.addHeader();
        component.updateHeader(1, { key: "x-api-key", value: "second" });
        expect(component.headerNameErrors()).toEqual(["duplicate", "duplicate"]);
        expect(component.canSave).toBe(false);

        component.updateHeader(1, { key: "X-Source" });
        expect(component.headerNameErrors()).toEqual([null, null]);
        expect(component.canSave).toBe(true);
      });

      it.each(["X Api", "X-Api:", "X-Ä", "X(1)", "X\\Api"])("refuses the header name %p", (key) => {
        component.addHeader();
        component.updateHeader(0, { key, value: "v" });
        expect(component.headerNameErrors()).toEqual(["invalid"]);
        expect(component.canSave).toBe(false);
      });

      it("accepts every character of an HTTP token", () => {
        component.addHeader();
        component.updateHeader(0, { key: "!#$%&'*+-.^_`|~09AZaz", value: "v" });
        expect(component.headerNameErrors()).toEqual([null]);
        expect(component.canSave).toBe(true);
      });

      it("refuses a header that has a value but no name", () => {
        component.addHeader();
        component.updateHeader(0, { key: "  ", value: "v" });
        expect(component.headerNameErrors()).toEqual(["required"]);
        expect(component.canSave).toBe(false);
      });

      it("leaves an empty row out of the save instead of refusing it", () => {
        component.addHeader();
        expect(component.headerNameErrors()).toEqual([null]);
        expect(component.canSave).toBe(true);
      });

      it("shows why a header row cannot be saved", async () => {
        component.addHeader();
        component.updateHeader(0, { key: "X-Api-Key", value: "first" });
        component.addHeader();
        component.updateHeader(1, { key: "X-API-KEY", value: "second" });
        await flush();

        const messages = Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll(".checkbox-error")).map(
          (element) => element.textContent ?? ""
        );
        expect(messages.length).toBe(2);
        expect(messages.every((message) => message.includes("Another header has the same name."))).toBe(true);
      });
    });

    describe("URL encoding of placeholder values", () => {
      const urlencodeCheckbox = (): HTMLElement | undefined =>
        Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-checkbox")).find((box) =>
          (box.textContent ?? "").includes("URL-Encode Placeholder Values")
        );

      it("is on for a new webhook", () => {
        expect(component.webhookModel().urlencode_values).toBe(true);
      });

      it.each([
        ["application/x-www-form-urlencoded", true],
        ["Application/X-WWW-Form-Urlencoded; charset=utf-8", true],
        ["application/json", false]
      ])("is offered for the content type %p: %p", async (content_type, offered) => {
        component.webhookModel.update((m) => ({ ...m, content_type }));
        await flush();
        expect(component.showUrlencodeValues()).toBe(offered);
        expect(urlencodeCheckbox() !== undefined).toBe(offered);
      });

      it("keeps its value while the content type changes", () => {
        component.webhookModel.update((m) => ({
          ...m,
          content_type: "application/x-www-form-urlencoded",
          urlencode_values: false
        }));
        component.webhookModel.update((m) => ({ ...m, content_type: "application/json" }));
        component.webhookModel.update((m) => ({ ...m, content_type: "application/x-www-form-urlencoded" }));
        expect(component.webhookModel().urlencode_values).toBe(false);
      });

      it("is saved with the webhook", async () => {
        fillRequired();
        component.webhookModel.update((m) => ({
          ...m,
          content_type: "application/x-www-form-urlencoded",
          urlencode_values: false
        }));

        await component.save();

        expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(
          expect.objectContaining({ urlencode_values: false }),
          {}
        );
      });
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
        }),
        {}
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

    it("treats a TLS-only edit as an unsaved change", () => {
      // The checkbox used to write straight into webhookModel, which changes the value without
      // marking the field dirty. hasChanges then stayed false - navigating away discarded the
      // edit without prompting - and canTest stayed true, so Test fired the *stored* TLS setting
      // while the form showed the new one.
      const tls = (Array.from(fixture.nativeElement.querySelectorAll("mat-checkbox")) as HTMLElement[]).find((box) =>
        (box.textContent || "").includes("Verify the server certificate")
      );
      expect(tls).toBeTruthy();
      expect(component.webhookModel().verify_tls).toBe(true);
      expect(component.hasChanges).toBe(false);
      expect(component.canTest()).toBe(true);

      (tls!.querySelector("input[type=checkbox]") as HTMLInputElement).click();
      fixture.detectChanges();

      expect(component.webhookModel().verify_tls).toBe(false);
      expect(component.hasChanges).toBe(true);
      // The test endpoint fires the stored definition, so it must be out of reach while the form
      // differs from it.
      expect(component.canTest()).toBe(false);
    });

    it("treats a cleared field as an unsaved change", async () => {
      // A clear button that wrote into webhookModel changed the value without marking the field
      // dirty: navigating away discarded the edit without a prompt, and Test fired the stored value.
      expect(component.hasChanges).toBe(false);
      expect(component.canTest()).toBe(true);

      clearButtonOf("Description").click();
      await flush();

      expect(component.webhookModel().description).toBe("");
      expect(component.webhookForm.description().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
      expect(component.canTest()).toBe(false);
    });

    it("loads the URL encoding setting of a stored webhook", async () => {
      // A webhook converted from an old WebHook handler has it off.
      webhookServiceMock.webhooks.set([{ ...STORED_WEBHOOK, urlencode_values: false }]);
      await flush();

      expect(component.webhookModel().urlencode_values).toBe(false);
    });

    it("loads the stored definition, headers included", () => {
      expect(component.isEditMode()).toBe(true);
      const model = component.webhookModel();
      expect(model.identifier).toBe("siem");
      expect(model.url).toBe("https://siem.example.com/hook");
      expect(model.timeout).toBe(5);
      expect(component.headers()).toEqual([
        { key: "X-Api-Key", value: WEBHOOK_CENSORED, secret: true, originalKey: "X-Api-Key" },
        { key: "X-Source", value: "privacyidea", secret: false, originalKey: "X-Source" }
      ]);
    });

    it("sends the censored placeholder back unchanged, keeping the stored secret", async () => {
      await component.save();
      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(
        expect.objectContaining({ headers: expect.objectContaining({ "X-Api-Key": WEBHOOK_CENSORED }) }),
        {}
      );
    });

    it("cannot save before the definition has arrived, and never to an empty identifier", async () => {
      // A reload or a deep link to /external-services/webhooks/details/siem renders while the
      // list is still loading: `data` is null and the form holds the empty defaults. Saving them
      // would POST the defaults over the stored webhook - and to /webhook/ rather than
      // /webhook/siem, because the identifier field is disabled in edit mode and a disabled field
      // skips its own required validator.
      webhookServiceMock.webhooks.set([]);
      component.webhookModel.update((m) => ({ ...m, identifier: "" }));
      component["data"] = null;

      expect(component.canSave).toBe(false);
      expect(await component.save()).toBe(false);
      expect(webhookServiceMock.postWebhook).not.toHaveBeenCalled();
    });

    it("addresses the webhook named by the route, not the one mirrored into the form", async () => {
      component.webhookModel.update((m) => ({ ...m, identifier: "", description: "changed" }));

      await component.save();

      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(expect.objectContaining({ identifier: "siem" }), {});
    });

    it("can test an unchanged definition, but not once it is edited", () => {
      expect(component.canTest()).toBe(true);
      component.updateHeader(0, { value: "new" });
      expect(component.canTest()).toBe(false);
    });

    it("tells the server which header a renamed one used to be", async () => {
      // The form only ever holds __CENSORED__ for a secret header, and that means "keep what is
      // stored under this name". Under the new name nothing is stored, so without saying that this
      // is a rename the credential is created empty and the save still reports success.
      component.updateHeader(0, { key: "X-API-Key" });

      await component.save();

      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: expect.objectContaining({ "X-API-Key": WEBHOOK_CENSORED })
        }),
        { "X-API-Key": "X-Api-Key" }
      );
    });

    it("reports no rename for a row that only changed its value", async () => {
      component.updateHeader(1, { value: "changed" });

      await component.save();

      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(expect.anything(), {});
    });

    it("reports no rename for a row the admin added", async () => {
      component.addHeader();
      component.updateHeader(2, { key: "X-New", value: "v" });

      await component.save();

      expect(webhookServiceMock.postWebhook).toHaveBeenCalledWith(expect.anything(), {});
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

  describe("without webhook_write", () => {
    beforeEach(async () => {
      await setUp("siem", ["webhook_read"]);
    });

    const buttonNamed = (label: string): HTMLButtonElement | undefined =>
      Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll("button")).find((button) =>
        (button.textContent ?? "").includes(label)
      );

    it("offers neither save nor the test call, which both need webhook_write", () => {
      expect(component.canSave).toBe(false);
      expect(component.canTest()).toBe(false);
      expect(buttonNamed("Save")?.disabled).toBe(true);
      expect(buttonNamed("Send test request")).toBeUndefined();
    });

    it("does not post the webhook", async () => {
      expect(await component.save()).toBe(false);
      expect(webhookServiceMock.postWebhook).not.toHaveBeenCalled();
    });
  });
});
