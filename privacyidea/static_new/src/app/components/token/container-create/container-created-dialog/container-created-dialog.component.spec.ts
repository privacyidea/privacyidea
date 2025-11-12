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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { firstValueFrom, of } from "rxjs";
import { signal } from "@angular/core";
import { Router } from "@angular/router";

import { ContainerCreatedDialogComponent } from "./container-created-dialog.component";
import { ContainerCreatedDialogWizardComponent } from "./container-created-dialog.wizard.component";
import { ContainerService } from "../../../../services/container/container.service";
import { ContentService } from "../../../../services/content/content.service";
import "@angular/localize/init";

describe("ContainerCreatedDialogComponent", () => {
  let fixture: ComponentFixture<ContainerCreatedDialogComponent>;
  let component: ContainerCreatedDialogComponent;

  const stopPolling = jest.fn();
  const containerServiceMock = { stopPolling };

  const containerSelected = jest.fn();
  const contentServiceMock = { containerSelected };

  const dialogClose = jest.fn();
  const dialogAfterClosed = jest.fn(() => of(true));
  const dialogRefMock = { close: dialogClose, afterClosed: dialogAfterClosed };

  const registerContainer = jest.fn((containerSerial: string, regenerate: boolean) => {});
  const matDialogData = signal({
    response: { result: { value: { container_url: { img: "" } } } },
    containerSerial: signal("C-001"),
    registerContainer
  });

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerCreatedDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: matDialogData },
        { provide: ContainerService, useValue: containerServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCreatedDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("calls containerService.stopPolling() when dialog closes", () => {
    expect(dialogAfterClosed).toHaveBeenCalled();
    expect(stopPolling).toHaveBeenCalledTimes(1);
  });

  it("containerSelected closes dialog and forwards selection", () => {
    component.containerSelected("C-777");
    expect(dialogClose).toHaveBeenCalled();
    expect(containerSelected).toHaveBeenCalledWith("C-777");
  });

  it("regenerateQRCode calls registerContainer with current serial and regenerate flag", () => {
    matDialogData.set({ ...matDialogData(), containerSerial: signal("C-123") });
    component.regenerateQRCode();
    expect(registerContainer).toHaveBeenCalledWith("C-123", true);
    expect(dialogClose).not.toHaveBeenCalled();
  });
});

describe("ContainerCreatedDialogWizardComponent", () => {
  let fixture: ComponentFixture<ContainerCreatedDialogWizardComponent>;
  let component: ContainerCreatedDialogWizardComponent;
  let httpMock: HttpTestingController;
  let authService: MockAuthService;

  const stopPolling = jest.fn();
  const containerServiceMock = { stopPolling };

  const containerSelected = jest.fn();
  const contentServiceMock = { containerSelected };

  const dialogClose = jest.fn();
  const dialogAfterClosed = jest.fn(() => of(true));
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
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerCreatedDialogWizardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: matDialogData },
        { provide: ContainerService, useValue: containerServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } }
      ]
    }).compileComponents();

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
    expect(stopPolling).toHaveBeenCalledTimes(1);
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
});
