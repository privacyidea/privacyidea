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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { firstValueFrom, Subject } from "rxjs";

import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { MockContainerService, MockContentService } from "@testing/mock-services";
import { ContainerTokenNotCreated } from "@services/container/container.service";
import { ContainerCreatedDialogComponent } from "./container-created-dialog.component";
import { ContainerCreatedDialogWizardComponent } from "./container-created-dialog.wizard.component";
import { axe } from "@testing/axe";

describe("ContainerCreatedDialogComponent", () => {
  let fixture: ComponentFixture<ContainerCreatedDialogComponent>;
  let component: ContainerCreatedDialogComponent;
  let afterClosed$: Subject<void>;
  let containerServiceMock: MockContainerService;
  let contentServiceMock: MockContentService;

  const dialogClose = jest.fn();
  const dialogAfterClosed = jest.fn(() => afterClosed$.asObservable());
  const dialogRefMock = { close: dialogClose, afterClosed: dialogAfterClosed };

  const registerContainer = jest.fn();
  const matDialogData = signal({
    response: { result: { value: { container_url: { img: "" } } } },
    containerSerial: signal("C-001"),
    registerContainer
  });

  beforeEach(async () => {
    afterClosed$ = new Subject();
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerCreatedDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: matDialogData },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } }
      ]
    }).compileComponents();

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;

    fixture = TestBed.createComponent(ContainerCreatedDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("calls containerService.stopPolling() when dialog closes", () => {
    expect(dialogAfterClosed).toHaveBeenCalled();
    expect(containerServiceMock.stopPolling).not.toHaveBeenCalled();
    afterClosed$.next(undefined);
    expect(containerServiceMock.stopPolling).toHaveBeenCalledTimes(1);
  });

  it("displays the container serial number in the dialog content", () => {
    const content = fixture.nativeElement.textContent as string;
    expect(content).toContain("C-001");
  });

  it("containerSelected closes dialog and forwards selection", () => {
    component.navigateContainerDetails("C-777");
    expect(dialogClose).toHaveBeenCalled();
    expect(contentServiceMock.navigateContainerDetails).toHaveBeenCalledWith("C-777");
  });

  it("regenerateQRCode calls registerContainer with current serial and regenerate flag", () => {
    matDialogData.set({ ...matDialogData(), containerSerial: signal("C-123") });
    component.regenerateQRCode();
    expect(registerContainer).toHaveBeenCalledWith("C-123", true);
    expect(dialogClose).not.toHaveBeenCalled();
  });

  describe("tokens the template did not create", () => {
    const notCreated: ContainerTokenNotCreated[] = [
      { type: "hotp", error: "Policy hotp_blocked forbids it", serial: "OATH0009" },
      { type: "totp", error: "Maximum number of tokens reached" }
    ];
    const baseData = () => ({
      response: { result: { value: { container_url: { img: "" } } } },
      containerSerial: signal("C-001"),
      registerContainer
    });
    const setData = (extra: Record<string, unknown>) => {
      matDialogData.set({ ...baseData(), ...extra } as unknown as ReturnType<typeof matDialogData>);
      fixture.detectChanges();
    };
    const text = () => fixture.nativeElement.textContent as string;
    const NONE = "None of the tokens of the template was created";

    afterEach(() => matDialogData.set(baseData()));

    it("lists every token that was not created as '<type> (<error>)'", () => {
      setData({ tokensNotCreated: notCreated });

      expect(text()).toContain("hotp (Policy hotp_blocked forbids it)");
      expect(text()).toContain("totp (Maximum number of tokens reached)");
      expect(fixture.nativeElement.querySelector(".error-message")).toBeNull();
    });

    it("uses the singular when one token was not created", () => {
      setData({ tokensNotCreated: [notCreated[0]] });

      const n = fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
      expect(n.textContent).toContain("This token of the template was not created:");
      expect(n.textContent).not.toContain("These tokens");
    });

    it("uses the plural when several tokens were not created", () => {
      setData({ tokensNotCreated: notCreated });

      const n = fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
      expect(n.textContent).toContain("These tokens of the template were not created:");
    });

    it("highlights as an error when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      const error = fixture.nativeElement.querySelector(".error-message") as HTMLElement;
      expect(error).toBeTruthy();
      expect(error.textContent).toContain(NONE);
      expect(text()).toContain("hotp (Policy hotp_blocked forbids it)");
    });

    it("shows a single heading when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      const notice = fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
      expect(notice.textContent).toContain("None of the tokens of the template was created:");
      expect(notice.textContent).not.toContain("These tokens of the template were not created");
    });

    it.each([[undefined], [[]]])("shows no notice when tokensNotCreated is %j", (value) => {
      setData({ tokensNotCreated: value });

      expect(text()).not.toContain("not created");
      expect(text()).not.toContain(NONE);
      expect(fixture.nativeElement.querySelector(".error-message")).toBeNull();
      expect(fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]')).toBeNull();
    });

    const withQr = { response: { result: { value: { container_url: { img: "data:image/png;base64,AAAA" } } } } };
    const notice = () => fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
    const title = () => (fixture.nativeElement.querySelector("[mat-dialog-title]") as HTMLElement).textContent!.trim();

    it("places the notice before the QR code", () => {
      setData({ ...withQr, tokensNotCreated: notCreated });

      const qr = fixture.nativeElement.querySelector("img.qr-code") as HTMLElement;
      expect(notice()).toBeTruthy();
      expect(qr).toBeTruthy();
      expect(notice().compareDocumentPosition(qr) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it("uses the red callout bar when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      expect(notice().classList).toContain("inline-callout-error");
      expect(notice().classList).toContain("inline-callout");
      expect(notice().classList).not.toContain("inline-warning");
      expect(notice().classList).not.toContain("inline-caution");
      expect(notice().classList).not.toContain("inline-callout-caution");
    });

    it("uses the red callout box when only some tokens were not created", () => {
      setData({ tokensNotCreated: notCreated });

      expect(notice().classList).toContain("inline-callout-error");
      expect(notice().classList).toContain("inline-callout");
      expect(notice().classList).not.toContain("inline-warning");
      expect(notice().classList).not.toContain("inline-caution");
      expect(notice().classList).not.toContain("inline-callout-caution");
    });

    it("titles the dialog 'Container Created Without Tokens' when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      expect(title()).toBe("Container Created Without Tokens");
    });

    it.each([["partial failure", { tokensNotCreated: notCreated }], ["no failure", {}]])(
      "keeps the title 'Container Successfully Created' on %s",
      (_name, extra) => {
        setData(extra);

        expect(title()).toBe("Container Successfully Created");
      }
    );
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});

describe("ContainerCreatedDialogWizardComponent", () => {
  let fixture: ComponentFixture<ContainerCreatedDialogWizardComponent>;
  let component: ContainerCreatedDialogWizardComponent;
  let httpMock: HttpTestingController;
  let afterClosed$: Subject<void>;
  let containerServiceMock: MockContainerService;

  const dialogClose = jest.fn();
  const dialogAfterClosed = jest.fn(() => afterClosed$.asObservable());
  const dialogRefMock = { close: dialogClose, afterClosed: dialogAfterClosed };

  const registerContainer = jest.fn();
  const matDialogData = signal({
    response: { result: { value: { container_url: { img: "" } } } },
    containerSerial: signal("C-001"),
    registerContainer
  });

  const flushInitialWizardRequests = () => {
    const topReq = httpMock.expectOne("/static/public/customize/container-create.wizard.post.top.html");
    expect(topReq.request.method).toBe("GET");
    topReq.flush("<div>TOP</div>");

    const bottomReq = httpMock.expectOne("/static/public/customize/container-create.wizard.post.bottom.html");
    expect(bottomReq.request.method).toBe("GET");
    bottomReq.flush("<div>BOTTOM</div>");
  };

  beforeEach(async () => {
    afterClosed$ = new Subject();
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerCreatedDialogWizardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: matDialogData },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } }
      ]
    }).compileComponents();

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;

    fixture = TestBed.createComponent(ContainerCreatedDialogWizardComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);

    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("creates", () => {
    flushInitialWizardRequests();
    expect(component).toBeTruthy();
  });

  it("subscribes to dialog close and calls stopPolling", () => {
    flushInitialWizardRequests();
    expect(dialogAfterClosed).toHaveBeenCalled();
    expect(containerServiceMock.stopPolling).not.toHaveBeenCalled();
    afterClosed$.next(undefined);
    expect(containerServiceMock.stopPolling).toHaveBeenCalledTimes(1);
  });

  it("exposes postTopHtml$ and postBottomHtml$; new subscriptions issue new GETs", async () => {
    flushInitialWizardRequests();
    const top$ = firstValueFrom(component.postTopHtml$);
    const topReq2 = httpMock.expectOne("/static/public/customize/container-create.wizard.post.top.html");
    expect(topReq2.request.method).toBe("GET");
    topReq2.flush("<div>TOP-AGAIN</div>");
    const topVal = await top$;
    expect(topVal).toBeTruthy();

    const bottom$ = firstValueFrom(component.postBottomHtml$);
    const bottomReq2 = httpMock.expectOne("/static/public/customize/container-create.wizard.post.bottom.html");
    expect(bottomReq2.request.method).toBe("GET");
    bottomReq2.flush("<div>BOTTOM-AGAIN</div>");
    const bottomVal = await bottom$;
    expect(bottomVal).toBeTruthy();
  });

  it("show loaded templates if not empty", async () => {
    // Mock HTTP responses for custom templates;
    httpMock.expectOne("/static/public/customize/container-create.wizard.post.top.html").flush("<div>Custom TOP</div>");
    httpMock
      .expectOne("/static/public/customize/container-create.wizard.post.bottom.html")
      .flush("<div>Custom BOTTOM</div>");
    fixture.detectChanges();

    const html = fixture.nativeElement.textContent;
    expect(html).toContain("Custom TOP");
    expect(html).toContain("Custom BOTTOM");
    // Optionally, check that default content is not present
    expect(html).not.toContain("Create Generic Container");
  });

  it("show default content if customization templates are empty", async () => {
    // Mock HTTP responses for custom templates;
    httpMock.expectOne("/static/public/customize/container-create.wizard.post.top.html").flush("");
    httpMock.expectOne("/static/public/customize/container-create.wizard.post.bottom.html").flush("");
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain("Container Successfully Created");
  });

  describe("tokens the template did not create", () => {
    const notCreated: ContainerTokenNotCreated[] = [
      { type: "hotp", error: "Policy hotp_blocked forbids it", serial: "OATH0009" },
      { type: "totp", error: "Maximum number of tokens reached" }
    ];
    const baseData = () => ({
      response: { result: { value: { container_url: { img: "" } } } },
      containerSerial: signal("C-001"),
      registerContainer
    });
    const setData = (extra: Record<string, unknown>) => {
      httpMock.expectOne("/static/public/customize/container-create.wizard.post.top.html").flush("");
      httpMock.expectOne("/static/public/customize/container-create.wizard.post.bottom.html").flush("");
      matDialogData.set({ ...baseData(), ...extra } as unknown as ReturnType<typeof matDialogData>);
      fixture.detectChanges();
    };
    const text = () => fixture.nativeElement.textContent as string;
    const NONE = "None of the tokens of the template was created";

    afterEach(() => matDialogData.set(baseData()));

    it("lists every token that was not created as '<type> (<error>)'", () => {
      setData({ tokensNotCreated: notCreated });

      expect(text()).toContain("hotp (Policy hotp_blocked forbids it)");
      expect(text()).toContain("totp (Maximum number of tokens reached)");
      expect(fixture.nativeElement.querySelector(".error-message")).toBeNull();
    });

    it("uses the singular when one token was not created", () => {
      setData({ tokensNotCreated: [notCreated[0]] });

      const n = fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
      expect(n.textContent).toContain("This token of the template was not created:");
      expect(n.textContent).not.toContain("These tokens");
    });

    it("uses the plural when several tokens were not created", () => {
      setData({ tokensNotCreated: notCreated });

      const n = fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
      expect(n.textContent).toContain("These tokens of the template were not created:");
    });

    it("highlights as an error when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      const error = fixture.nativeElement.querySelector(".error-message") as HTMLElement;
      expect(error).toBeTruthy();
      expect(error.textContent).toContain(NONE);
      expect(text()).toContain("hotp (Policy hotp_blocked forbids it)");
    });

    it("shows a single heading when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      const notice = fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
      expect(notice.textContent).toContain("None of the tokens of the template was created:");
      expect(notice.textContent).not.toContain("These tokens of the template were not created");
    });

    it.each([[undefined], [[]]])("shows no notice when tokensNotCreated is %j", (value) => {
      setData({ tokensNotCreated: value });

      expect(text()).not.toContain("not created");
      expect(text()).not.toContain(NONE);
      expect(fixture.nativeElement.querySelector(".error-message")).toBeNull();
      expect(fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]')).toBeNull();
    });

    const withQr = { response: { result: { value: { container_url: { img: "data:image/png;base64,AAAA" } } } } };
    const notice = () => fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement;
    const title = () => (fixture.nativeElement.querySelector("[mat-dialog-title]") as HTMLElement).textContent!.trim();

    it("places the notice before the QR code", () => {
      setData({ ...withQr, tokensNotCreated: notCreated });

      const qr = fixture.nativeElement.querySelector("img.qr-code") as HTMLElement;
      expect(notice()).toBeTruthy();
      expect(qr).toBeTruthy();
      expect(notice().compareDocumentPosition(qr) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it("uses the red callout bar when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      expect(notice().classList).toContain("inline-callout-error");
      expect(notice().classList).toContain("inline-callout");
      expect(notice().classList).not.toContain("inline-warning");
      expect(notice().classList).not.toContain("inline-caution");
      expect(notice().classList).not.toContain("inline-callout-caution");
    });

    it("uses the red callout box when only some tokens were not created", () => {
      setData({ tokensNotCreated: notCreated });

      expect(notice().classList).toContain("inline-callout-error");
      expect(notice().classList).toContain("inline-callout");
      expect(notice().classList).not.toContain("inline-warning");
      expect(notice().classList).not.toContain("inline-caution");
      expect(notice().classList).not.toContain("inline-callout-caution");
    });

    it("titles the dialog 'Container Created Without Tokens' when none of the tokens was created", () => {
      setData({ tokensNotCreated: notCreated, allTokensFailed: true });

      expect(title()).toBe("Container Created Without Tokens");
    });

    it.each([["partial failure", { tokensNotCreated: notCreated }], ["no failure", {}]])(
      "keeps the title 'Container Successfully Created' on %s",
      (_name, extra) => {
        setData(extra);

        expect(title()).toBe("Container Successfully Created");
      }
    );
  });
});
