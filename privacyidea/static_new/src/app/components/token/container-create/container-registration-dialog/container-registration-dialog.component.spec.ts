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
import { ContainerRegistrationDialogComponent } from "./container-registration-dialog.component";
import { provideHttpClient } from "@angular/common/http";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { signal } from "@angular/core";
import { ContainerService } from "../../../../services/container/container.service";
import { ContentService } from "../../../../services/content/content.service";
import { Router } from "@angular/router";


describe("ContainerRegistrationDialogComponent", () => {
  let fixture: ComponentFixture<ContainerRegistrationDialogComponent>;
  let component: ContainerRegistrationDialogComponent;

  const stopPolling = jest.fn();
  const containerServiceMock = { stopPolling };

  const containerSelected = jest.fn();
  const contentServiceMock = { containerSelected };

  const dialogClose = jest.fn();
  const dialogAfterClosed = jest.fn(() => of(true));
  const dialogRefMock = { close: dialogClose, afterClosed: dialogAfterClosed };

  const registerContainer = jest.fn();
  const matDialogData = {
    response: { result: { value: { container_url: { img: "" } } } },
    containerSerial: signal("C-001"),
    registerContainer
  };

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationDialogComponent],
      providers: [
        provideHttpClient(),

        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: matDialogData },
        { provide: ContainerService, useValue: containerServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerRegistrationDialogComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("calls containerService.stopPolling() when the dialog is closed (constructor subscription)", () => {
    expect(dialogAfterClosed).toHaveBeenCalled();
    expect(stopPolling).toHaveBeenCalledTimes(1);
  });

  it("containerSelected closes the dialog and forwards selection to ContentService", () => {
    component.containerSelected("C-777");
    expect(dialogClose).toHaveBeenCalled();
    expect(containerSelected).toHaveBeenCalledWith("C-777");
  });

  it("regenerateQRCode calls registerContainer with current serial and closes the dialog", () => {
    matDialogData.containerSerial.set("C-123");

    component.regenerateQRCode();

    expect(registerContainer).toHaveBeenCalledWith("C-123");
    expect(dialogClose).toHaveBeenCalled();
  });
});

