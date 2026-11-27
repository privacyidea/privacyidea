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
import { PRIMARY_OUTLET, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { WebhooksComponent } from "@components/external-services/webhooks/webhooks.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { Webhook, WebhookService } from "@services/webhook/webhook.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService, MockDialogService, MockTableUtilsService, MockWebhookService } from "@testing/mock-services";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { setRights } from "@testing/toolbar-actions";
import { Subject } from "rxjs";

describe("WebhooksComponent", () => {
  let component: WebhooksComponent;
  let fixture: ComponentFixture<WebhooksComponent>;
  let webhookServiceMock: MockWebhookService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  const buildWebhook = (identifier: string, overrides: Partial<Webhook> = {}): Webhook => ({
    identifier,
    url: `https://${identifier}.example.com/hook`,
    http_method: "POST",
    content_type: "application/json",
    auth_type: "none",
    verify_tls: true,
    timeout: 3,
    urlencode_values: true,
    headers: {},
    secret_headers: [],
    ...overrides
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WebhooksComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: WebhookService, useClass: MockWebhookService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    webhookServiceMock = TestBed.inject(WebhookService) as unknown as MockWebhookService;
    webhookServiceMock.webhooks.set([
      buildWebhook("siem", { auth_type: "header" }),
      buildWebhook("chat", { http_method: "PUT" })
    ]);

    fixture = TestBed.createComponent(WebhooksComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    jest.spyOn(router, "navigate").mockResolvedValue(true);
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "webhook_read"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the webhooks from the service", () => {
    expect(component.webhookDataSource().data.length).toBe(2);
    expect(component.webhookDataSource().data[0].identifier).toBe("siem");
  });

  it("should filter the webhooks", () => {
    component.onFilterInput("siem");
    expect(component.webhookDataSource().filter).toBe("siem");
  });

  it("should only select the rows left by the filter", async () => {
    component.onFilterInput("siem");
    fixture.detectChanges();
    await fixture.whenStable();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.identifier)).toEqual(["siem"]);
  });

  it("should navigate to the create page", () => {
    component.onCreateNewWebhook();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS_NEW);
  });

  it("should navigate to the edit page", () => {
    const webhook = webhookServiceMock.webhooks()[0];
    component.onEditWebhook(webhook);
    expect(router.navigate).toHaveBeenCalledWith([ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS_DETAILS, webhook.identifier]);
  });

  it.each(["hook(1)", "Notify SIEM (prod)", "50% & more;"])(
    "keeps the identifier %p whole on its way to the editor",
    (identifier) => {
      // The editor restricts an identifier to [a-zA-Z0-9._-], but the server also accepts one created
      // through the API or a config import. encodeURIComponent() leaves "(" and ")" as they are, and
      // the router ends a path segment at "(": "hook(1)" opened the editor of "hook".
      component.onEditWebhook(buildWebhook(identifier));
      const commands = [ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS_DETAILS, identifier];
      expect(router.navigate).toHaveBeenCalledWith(commands);

      const url = router.serializeUrl(router.createUrlTree(commands));
      const segments = router.parseUrl(url).root.children[PRIMARY_OUTLET].segments;
      expect(segments.map((segment) => segment.path)).toEqual(["external-services", "webhooks", "details", identifier]);
    }
  );

  it("keeps the filter when the rows are replaced", async () => {
    // The data source is rebuilt whenever the list changes - a delete, or the reload button. A
    // filter written onto the old instance was lost there, so the full list reappeared while the
    // input still showed what it was filtered by.
    component.onFilterInput("siem");
    fixture.detectChanges();
    await fixture.whenStable();
    expect(component.webhookDataSource().filteredData.map((row) => row.identifier)).toEqual(["siem"]);

    webhookServiceMock.webhooks.set([buildWebhook("siem"), buildWebhook("chat"), buildWebhook("siem2")]);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.filterString()).toBe("siem");
    expect(component.webhookDataSource().filteredData.map((row) => row.identifier)).toEqual(["siem", "siem2"]);
  });

  it("should delete the selected webhook after confirmation", () => {
    component.selector.selectRow(webhookServiceMock.webhooks()[0]);
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(webhookServiceMock.deleteWebhook).toHaveBeenCalledWith("siem");
  });

  it("should not delete anything when the confirmation is dismissed", () => {
    component.selector.selectRow(webhookServiceMock.webhooks()[0]);
    component.deleteSelected();
    confirmClosed.next(false);
    confirmClosed.complete();

    expect(webhookServiceMock.deleteWebhook).not.toHaveBeenCalled();
  });

  describe("webhook_write", () => {
    const buttonLabels = (): string[] =>
      Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll("button")).map(
        (button) => button.textContent?.trim() ?? ""
      );
    const selectColumn = (): Element | null => fixture.nativeElement.querySelector("th.mat-column-select");

    it("offers create, delete and row selection with webhook_write", () => {
      setRights(fixture, ["webhook_read", "webhook_write"]);

      expect(component.displayedColumns()).toContain("select");
      expect(selectColumn()).not.toBeNull();
      expect(buttonLabels().some((label) => label.includes("Create Webhook"))).toBe(true);
      expect(buttonLabels().some((label) => label.includes("Delete"))).toBe(true);
    });

    it("hides create, delete and row selection without webhook_write", () => {
      // POST and DELETE on /webhook/ need webhook_write, so these would only end in a 403.
      setRights(fixture, ["webhook_read"]);

      expect(component.displayedColumns()).not.toContain("select");
      expect(selectColumn()).toBeNull();
      expect(buttonLabels().some((label) => label.includes("Create Webhook"))).toBe(false);
      expect(buttonLabels().some((label) => label.includes("Delete"))).toBe(false);
    });
  });

  describe("empty state", () => {
    beforeEach(() => {
      webhookServiceMock.webhooks.set([]);
    });

    it("offers the create button and hint with webhook_write", () => {
      setRights(fixture, ["webhook_read", "webhook_write"]);

      const state: HTMLElement = fixture.nativeElement.querySelector("app-table-state");
      expect(state.querySelector("button")?.textContent).toContain("Create Webhook");
      expect(state.textContent).toContain("Create a webhook to notify another system");
    });

    it("offers neither button nor hint without webhook_write", () => {
      setRights(fixture, ["webhook_read"]);

      const state: HTMLElement = fixture.nativeElement.querySelector("app-table-state");
      expect(state.querySelector("button")).toBeNull();
      expect(state.textContent).not.toContain("Create a webhook to notify another system");
    });
  });

  it("names the table and the selection checkboxes for assistive technology", () => {
    setRights(fixture, ["webhook_read", "webhook_write"]);

    expect(fixture.nativeElement.querySelector("table").getAttribute("aria-label")).toBe("Webhooks");
    const checkboxLabels = Array.from<HTMLInputElement>(
      fixture.nativeElement.querySelectorAll("mat-checkbox input[type=checkbox]")
    ).map((input) => input.getAttribute("aria-label"));
    expect(checkboxLabels).toEqual(["Select all rows", "Select row", "Select row"]);
  });
});
